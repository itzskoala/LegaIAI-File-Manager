
#for contracts but keep in mind that every document can be different doesn't fit this schema
class ContractMetadata(BaseModel):
    brand: str                          # required
    counterparty: str                   # required
    agreement_type: str                 # required
    effective_date: Optional[date] = None
    fiscal_year: Optional[str] = None   # FY25, FY26, etc.
    status: AgreementStatus = AgreementStatus.unknown
    needs_review: bool = False


