class LambdaContractError(Exception):
    """Base class for all handled errors in this Lambda."""
    pass

class ValidationError(LambdaContractError):
    def __init__(self, message=None, missing_fields=None):
        self.missing_fields = missing_fields

        if missing_fields:
            final_message = f"Missing required fields: {', '.join(missing_fields)}"

        elif message:
            final_message = message
        
        else:
            raise ValueError("ValidatioError requires either 'message' or 'missing_fields'")

        self.message = final_message
        super().__init__(final_message)
            

class RetrieveError(LambdaContractError):
    ...

class FilingNotFoundError(RetrieveError):
    ...

class TickerNotFoundError(RecursionError):
    ...

class ExtractError(LambdaContractError):
    ...

class InvokeError(LambdaContractError):
   ...

