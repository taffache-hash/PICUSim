"""
BaseModule
==========
Interfaccia astratta che tutti i moduli fisiologici devono implementare.

Un modulo è responsabile di:
  1. Dichiarare le proprie variabili di INPUT (lette dal Bus)
  2. Dichiarare le proprie variabili di OUTPUT (scritte nel Bus)
  3. Implementare step(bus, dt) che aggiorna il proprio stato interno
     e scrive gli output nel Bus

L'Engine chiama step() su ogni modulo registrato in ordine.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .bus import PhysiologicalBus


class BaseModule(ABC):
    """
    Classe base astratta per ogni modulo fisiologico del Digital Twin.
    """

    def __init__(self, name: str, params: Dict[str, Any] | None = None):
        self.name = name
        self.params: Dict[str, Any] = params or {}
        self._initialized: bool = False
        self._step_count: int = 0

    # --- Metodi da implementare obbligatoriamente ---

    @property
    @abstractmethod
    def input_keys(self) -> List[str]:
        """Variabili che il modulo legge dal Bus (documentazione + validazione)."""
        ...

    @property
    @abstractmethod
    def output_keys(self) -> List[str]:
        """Variabili che il modulo scrive nel Bus."""
        ...

    @abstractmethod
    def initialize(self, bus: "PhysiologicalBus") -> None:
        """
        Inizializzazione one-shot all'avvio della simulazione.
        Qui si calcolano i parametri derivati e si portano le variabili
        del Bus ai valori baseline del modulo.
        """
        ...

    @abstractmethod
    def step(self, bus: "PhysiologicalBus", dt: float) -> None:
        """
        Avanza il modulo di un timestep dt [s].
        Legge dal Bus, aggiorna lo stato interno, scrive nel Bus.
        """
        ...

    # --- Metodi opzionali con implementazione di default ---

    def reset(self, bus: "PhysiologicalBus") -> None:
        """Reset al baseline. Override se necessario."""
        self._step_count = 0
        self._initialized = False
        self.initialize(bus)

    def validate_params(self) -> None:
        """Validazione dei parametri. Override per check specifici."""
        pass

    def get_param(self, key: str, default: Any = None) -> Any:
        """Lettura sicura di un parametro con fallback."""
        return self.params.get(key, default)

    def __repr__(self) -> str:
        status = "initialized" if self._initialized else "not initialized"
        return f"<{self.__class__.__name__} '{self.name}' [{status}] steps={self._step_count}>"
