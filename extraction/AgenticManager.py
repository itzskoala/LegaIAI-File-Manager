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

        #think file at a time
        #I have all the text strcutred as text...from the pydantic object
        # my only goal is to name the file
        # name first, then strcutre the folders? hmmmm....Yeah I think that makes sense
        # folder strucutre seems very basic 
        # how do we do this 
        # read the file with AI, ollama/claude fills in the fields accordingly 
        # we need to verify? How? 
        # concerns: reading the whole file for a naming convention feels like its too much?
            # -> Is there an easier way to do this? 
            # -> what do the job requiremnts say? vs. what do I think is better? 
            # read a documnet to extract data to conform to a pydantic/strcutred output ...
            # is there a way to do this without reading everything? Portions? 
            # how to search for info with reading the entrie doc?
            # as soon as you have all the info stop searching/scanning
            # partial scan, prime the AI where to look
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


    

    



    
