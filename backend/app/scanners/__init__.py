"""Scanner adapter modules."""

from app.scanners.base import BaseScannerAdapter, ScanResult
from app.scanners.nmap_adapter import NmapScannerAdapter
from app.scanners.nuclei_adapter import NucleiScannerAdapter
from app.scanners.zap_adapter import ZapScannerAdapter

__all__ = [
    "BaseScannerAdapter",
    "ScanResult",
    "NmapScannerAdapter",
    "NucleiScannerAdapter",
    "ZapScannerAdapter",
    "SCANNER_REGISTRY",
    "get_scanner",
]

SCANNER_REGISTRY: dict[str, type[BaseScannerAdapter]] = {
    "nmap": NmapScannerAdapter,
    "nuclei": NucleiScannerAdapter,
    "zap": ZapScannerAdapter,
}


def get_scanner(scanner_type: str) -> BaseScannerAdapter:
    adapter_class = SCANNER_REGISTRY.get(scanner_type)
    if not adapter_class:
        raise ValueError(f"Unknown scanner type: {scanner_type}")
    return adapter_class()
