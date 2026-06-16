from typing import Union, List
from pydantic import BaseModel, Field, field_validator, model_validator

#for contracts but keep in mind that every document can be different doesn't fit this schema
#QUESTION: DO ALL DOCUMENTS HAVE THE SAME SCHEMA!?

class Schema(BaseModel):
    counterparty: str = Field(
        description="This should be the full legal entity name as stated in the preamble of the agreement. "
                    "Avoid commonly used acronyms used in our industry unless obvious, e.g NPR. "
                    "For individuals, use LastNameFirstName."
    )
    agreement_type: Union[str, List[str]] = Field(
        description="This is almost always the title at the top of the agreement. "
                    "Sometimes two agreements are combined into one document, usually a governing agreement "
                    "and sub-agreement such as a master services agreement and order form, or SOW. "
                    "Name both agreements."
    )
    helpful_phrase: str = Field(
        description="A one line summary of what this document is about. This can be very short and vary greatly "
                    "depending on the services or relationship. It aids in identifying contracts at a glance, "
                    "and distinguishing among several contracts with the same counterparty. "
                    "It connects back to the counterparty in a meaningful way."
    )
    brand: str = Field(
        description="The APMG brand for which services are provided or revenue created. "
                    "This is MPR, MPR News, LAist, The Current, YourClassical, Marketplace, or APM."
                    "Exceptions for corporate departments: APMG IT, APMG HR, MPR Faclities, APMG Braodcast Ops, Glen Nelson Center, MPR Development, etc..."
    )
    date: str = Field(
        description="The date of the document in YYYY-MM-DD format."
        #TODO: this is incorrect
    )
    # confidence: float = Field(
    #     ge=0, le=1,
    #     description="Confidence score between 0 and 1 on the accuracy of the extraction."
    # )
    # @field_validator("confidence", mode="before")
    # @classmethod
    # def normalize_confidence(cls, v):
    #     v = float(v)
    #     if v > 1:
    #         v = v / 100
    #     return max(0.0, min(1.0, v))       # always tagged on the end of the file name
    needs_review: bool = False      # flagged True if confidence is low — routes to unprocessed folder

    @model_validator(mode='after')
    def flag_incomplete(self) -> 'Schema':
        empty = {'', 'unknown', 'n/a', 'none', 'null'}
        fields_to_check = [self.counterparty, self.helpful_phrase, self.brand, self.date]
        if any(str(v).strip().lower() in empty for v in fields_to_check):
            self.needs_review = True
        return self
