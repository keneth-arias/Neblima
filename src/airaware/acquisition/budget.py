"""Presupuesto de payload compartido por las tareas de un lote."""

import threading

from airaware.acquisition.models import AcquisitionError


class ByteBudget:
    """Contabilizar payload recibido entre tareas e intentos, de manera sincronizada."""

    def __init__(self, limit: int):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise AcquisitionError("El presupuesto de red debe ser un entero positivo")
        self.limit = limit
        self.used = 0
        self._lock = threading.Lock()

    def check_remaining(self) -> None:
        with self._lock:
            if self.used >= self.limit:
                raise AcquisitionError("Se agotó el presupuesto total de bytes de red")

    def consume(self, size: int) -> None:
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise AcquisitionError("El consumo debe ser un entero no negativo")
        with self._lock:
            self.used += size
            if self.used > self.limit:
                raise AcquisitionError("Se agotó el presupuesto total de bytes de red")
