from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime

#This is the base class for the sources
# I am using a Strategy Design Pattern where all new Children/source types will be forced to implement the same functions defined in the Base Class

class DocumentRecord(BaseModel):
    source_type: str      # "local", "outlook", "leap"
    source_id: str        # file path, email id, leap document id, etc.
    title: str            # filename, email subject, document title
    content: str          # extracted text
    date: str             # extra info
    # original_path: str | None = None
    # sender: str | None = None
    # received_at: str | None = None
    # file_extension: str | None = None
    # created_at: datetime | None = None
    # modified_at: datetime | None = None
    # author: str | None = None
    # checksum: str | None = None
    # source_system: str | None = None


class DocumentSource(ABC):  #source of files 
    @abstractmethod
    def load_documents(self) -> list[DocumentRecord]:
        pass
    