 """Abstract backend definition."""

 from __future__ import annotations

 from abc import ABC, abstractmethod
 from typing import Dict, List, Optional


 class PromptBackend(ABC):
     """Interface all backends must implement."""

     @abstractmethod
     def add(self, name: str, content: str, metadata: Dict[str, object]) -> None:
         raise NotImplementedError

     @abstractmethod
     def get(self, name: str, version: Optional[int] = None) -> Dict[str, object]:
         raise NotImplementedError

     @abstractmethod
     def update(self, name: str, content: str, metadata: Dict[str, object]) -> None:
         raise NotImplementedError

     @abstractmethod
     def delete(self, name: str, version: Optional[int] = None) -> None:
         raise NotImplementedError

     @abstractmethod
     def list(self, filters: Optional[Dict[str, object]] = None) -> List[Dict[str, object]]:
         raise NotImplementedError

