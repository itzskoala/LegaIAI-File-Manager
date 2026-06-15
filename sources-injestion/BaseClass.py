from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

#This is the base class for the sources
# I am using a Strategy Design Pattern where all new Children/source types will be forced to implement the same functions defined in the Base Class
# What are those functions you ask? 
# retrive_files()
# convert_to_obj() ?
# convert_to_text() ?

#I also think from there we can create more classes for the Pdf stuff...let's get there when I get there... :)
# Abstract Class in Python


# You use it when you have multiple classes that should follow the same structure, but each one does the details differently.
# When to use it? Use one when you want to force all source types to have the same methods and output... :)


#probably am going to have to change these types
#This is what the AI will read, just the content? or the whole pydanic obj? 
#is this pydantic?
# pydantic might be better because it's strongly typed 


# @dataclass
# class DocumentRecord:
#     source_type: str
#     source_id: str
#     title: str
#     content: str

class DocumentRecord(BaseModel):
    source_type: str
    source_id: str
    title: str
    content: str
    date: str
    # original_path: str | None = None
    # sender: str | None = None
    # received_at: str | None = None
    # file_extension: str | None = None


class DocumentSource(ABC):  #source of files 
    @abstractmethod
    def load_documents(self) -> list[DocumentRecord]:
        pass
    
    

