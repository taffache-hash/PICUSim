"""
SimulationEngine
================
Loop principale della simulazione.

Responsabilità:
  - Registrare i moduli e ordinarli per esecuzione
  - Gestire il timestep (fisso o adattivo)
  - Applicare le perturbazioni dalla timeline dello scenario
  - Raccogliere la history dal Bus
  - Restituire i risultati come DataFrame pandas
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Callable, Optional
import time
import logging

from .bus import PhysiologicalBus, BusState
from .base_module import BaseModule
from .quality import SimulationError, check_state

logger = logging.getLogger("PDT.Engine")


# ---------------------------------------------------------------------------
# Perturbazione schedulata
# ---------------------------------------------------------------------------

class Perturbation:
    """
    Un evento che modifica il Bus a un tempo specificato.
    
    Examples
    --------
    >>> p = Perturbation(t=30.0, key="PEEP", value=10.0, label="PEEP step 5→10")
    >>> p = Perturbation(t=60.0, callback=lambda bus: bus.set("HR", 140), label="Tachicardia")
    """

    def __init__(
        self,
        t: float,
        key: str | None = None,
        value: Any = None,
        callback: Callable[[PhysiologicalBus], None] | None = None,
        label: str = ""
    ):
        if key is None and callback is None:
            raise ValueError("Perturbation richiede 'key' o 'callback'.")
        self.t = t
        self.key = key
        self.value = value
        self.callback = callback
        self.label = label
        self._applied = False

    def apply(self, bus: PhysiologicalBus) -> None:
        if self._applied:
            return
        if self.callback:
            self.callback(bus)
        else:
            # v3.1 Step 4.48: support educational multiplier perturbations
            # such as lactate_multiplier, SaO2_multiplier, PaCO2_multiplier.
            # The multiplier field itself is stored for audit, and if the
            # corresponding base variable exists it is applied immediately.
            if isinstance(self.key, str) and self.key.endswith("_multiplier"):
                bus.set(self.key, self.value)
                base_key = self.key[:-11]
                if hasattr(bus.state, base_key):
                    try:
                        bus.set(base_key, float(bus.get(base_key)) * float(self.value))
                    except Exception:
                        pass
            else:
                bus.set(self.key, self.value)
        self._applied = True
        logger.info(f"  [t={self.t:.1f}s] Perturbazione: {self.label or self.key}={self.value}")

    def reset(self) -> None:
        self._applied = False


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """
    Motore di simulazione del Pediatric Digital Twin.
    
    Usage
    -----
    >>> engine = SimulationEngine(bus, dt=0.02)
    >>> engine.register(RespiratoryModule(params))
    >>> engine.register(CardiovascularModule(params))
    >>> engine.add_perturbation(Perturbation(t=30, key="PEEP", value=10))
    >>> results = engine.run(T=120.0)
    """

    def __init__(
        self,
        bus: PhysiologicalBus,
        dt: float = 0.02,          # [s] timestep di default
        snapshot_every: int = 5,   # salva ogni N step (riduce memoria)
        verbose: bool = True
    ):
        self.bus = bus
        self.dt = dt
        self.snapshot_every = snapshot_every
        self.verbose = verbose
        self._modules: List[BaseModule] = []
        self._perturbations: List[Perturbation] = []
        self._initialized = False

    # --- Registrazione moduli ---

    def register(self, module: BaseModule) -> "SimulationEngine":
        """
        Aggiunge un modulo al pipeline.
        I moduli vengono eseguiti nell'ordine di registrazione.
        Restituisce self per chaining.
        """
        self._modules.append(module)
        logger.info(f"Modulo registrato: {module.name}")
        return self

    def add_perturbation(self, p: Perturbation) -> "SimulationEngine":
        """Aggiunge una perturbazione schedulata."""
        self._perturbations.append(p)
        return self

    def add_perturbations(self, perturbs: List[Perturbation]) -> "SimulationEngine":
        for p in perturbs:
            self.add_perturbation(p)
        return self

    # --- Inizializzazione ---

    def _initialize(self) -> None:
        """Inizializza tutti i moduli in ordine."""
        if self.verbose:
            print(f"[PDT] Inizializzazione {len(self._modules)} moduli...")
        for m in self._modules:
            m.initialize(self.bus)
            m._initialized = True
            if self.verbose:
                print(f"  [ok] {m.name}")
        # reset perturbazioni
        for p in self._perturbations:
            p.reset()
        self.bus.reset_history()
        check_state(self.bus, t=self.bus.state.t, module_name="initialize")
        self._initialized = True

    # --- Loop principale ---

    def run(self, T: float, t_start: float = 0.0) -> pd.DataFrame:
        """
        Esegue la simulazione da t_start a t_start + T.
        
        Parameters
        ----------
        T        : durata simulazione [s]
        t_start  : tempo iniziale [s]
        
        Returns
        -------
        DataFrame pandas con tutte le variabili del Bus nel tempo.
        """
        self._initialize()

        t = t_start
        t_end = t_start + T
        step_n = 0
        wall_start = time.perf_counter()

        self.bus.state.t = t
        self.bus.snapshot()  # snapshot t=0

        n_steps_total = int(T / self.dt)
        report_interval = max(1, n_steps_total // 20)  # 20 report durante la sim

        if self.verbose:
            print(f"[PDT] Simulazione: T={T}s, dt={self.dt}s, "
                  f"steps={n_steps_total}, moduli={len(self._modules)}")
            print(f"{'-'*60}")

        while t < t_end - 1e-9:
            # 1. Applica perturbazioni pendenti
            for p in self._perturbations:
                if not p._applied and t >= p.t:
                    p.apply(self.bus)

            # 2. Step di tutti i moduli in ordine
            for m in self._modules:
                try:
                    m.step(self.bus, self.dt)
                    m._step_count += 1
                    check_state(self.bus, t=t, module_name=m.name)
                except SimulationError:
                    raise
                except Exception as e:
                    raise RuntimeError(
                        f"Errore nel modulo '{m.name}' a t={t:.3f}s: {e}"
                    ) from e

            # 3. Avanza il tempo
            t += self.dt
            self.bus.set("t", t)

            # 4. Snapshot
            step_n += 1
            if step_n % self.snapshot_every == 0:
                self.bus.snapshot()

            # 5. Progress report
            if self.verbose and step_n % report_interval == 0:
                s = self.bus.state
                pct = (t - t_start) / T * 100
                print(f"  t={t:6.1f}s ({pct:4.0f}%) | "
                      f"SaO2={s.SaO2*100:.1f}% | "
                      f"MAP={s.MAP:.0f} mmHg | "
                      f"CO={s.CO:.2f} L/min | "
                      f"Paw={s.Paw:.1f} cmH2O")

        # Snapshot finale
        self.bus.snapshot()

        wall_elapsed = time.perf_counter() - wall_start
        if self.verbose:
            print(f"{'-'*60}")
            print(f"[PDT] Completato in {wall_elapsed:.2f}s wall-clock. "
                  f"Snapshots: {len(self.bus.history)}")

        return self._to_dataframe()

    # --- Export ---

    def _to_dataframe(self) -> pd.DataFrame:
        """Converte la history del Bus in DataFrame."""
        if not self.bus.history:
            return pd.DataFrame()
        records = []
        for s in self.bus.history:
            records.append(s.__dict__.copy())
        return pd.DataFrame(records).set_index("t")

    def save_csv(self, path: str) -> None:
        """Salva i risultati in CSV."""
        df = self._to_dataframe()
        df.to_csv(path)
        print(f"[PDT] Risultati salvati in: {path}")

