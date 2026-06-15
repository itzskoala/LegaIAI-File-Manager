import ollama

from LocalFileSource import LocalFileSource
# from EmailFileSource import EmailFileSource
# from SharepointFileSource import SharepointFileSource

#AI portion
# this will take in strucutred output the Document Record obj
# it will read the entire obj? Or just the text of the documnet?
# probably txt for now, everyhting else I can hard code
# do I need another strucutred output for what the AI will give?
# I should be able to read just the file name and create a naming convention???
# pontentially this is true???

# we need yamal files/json strucutre 
# going to try using Ollama/Claude?
# 

# tools = 

class AgenticManager(LocalFileSource):
    def __init__(self, LocalFileSource):
        # LocalFileSource

    def ai_extraction():
        #for when we can't fall back and need to extract document details...
        #most times we can tell where to put a document based off of its details 
        
        #or maybe we just actually have to do this for each doc...?
        #how do we name an excell file? 
            #-> The lowkey just use the BaseModel fields to piece it together ...
        #

        response = ollama.chat(
            model="gemma3",
            messages=[{
                "role": "user",
                "content": f"Extract contract metadata from this document:\n\n{text[:4000]}"
            }],
            format=ContractMetadata.model_json_schema()
        )

    def naming_convention():
        #The naming convention must be {Counterparty} - {AgreementType} - {Brand} ({YYYY-MM-DD}) ({Status}).{ext}

        

    def confidence_check():
        #call another LLM?
        #how else can we do a confidence check?


    

    



    
