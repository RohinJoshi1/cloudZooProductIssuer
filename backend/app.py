from flask import Flask, request, jsonify
import base64
import json
import requests
from typing import Dict, List, Optional,Any
from dataclasses import dataclass, asdict
from uuid import UUID
from functools import wraps
from flask_cors import CORS
import os 
from config import Config

import dotenv 
dotenv.load_dotenv(dotenv.find_dotenv()) 
app = Flask(__name__) 
CORS(app, resources={
    r"/api/*": {
        "origins": Config.CORS_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

'''
Example Body: 
{
    "id": "06eb1079-5a56-47a1-aw6d-0b4518fd894b",
    "creationDate": 1559928168,
    "iss": "mcneel",
    "format": {
        "length": {
            "min": 24,
            "max": 24
        },
        "prefix": "RMA7-",
        "example": "RMA7-XXXX-XXXX-XXXX-XXXX-XXXX",
        "regexFilter": "[A-Za-z0-9]"
    },
    "version": "6",
    "platforms": [
        "Windows"
    ],
    "picture": "https://elisapi.mcneel.com/media/2",
    "downloadUrl": "https://www.rhino3d.com/download/rhino-for-mac/6/wip",
    "titles": {
        "en": "Rhino WIP"
    },
}

Description
id (readonly) - A lowercase GUID that uniquely describes each product. This GUID must be unique in the entire system.
creationDate (readonly) - A unix timestamp in seconds representing the date the product was added to Cloud Zoo.
iss (readonly) - The id of the issuer as registered with Cloud Zoo.
format - A License Format object. Cloud Zoo will send all requests to add a license to the system to the issuer of the product whose license format matches the given license key.
version - The version of the product that this license represents. This string is user facing and will be used in Rhino as well as in the Licenses Portal.
platforms - An array of supported platforms for this license. Currently, only Windows and Mac are supported.
picture - A url where an icon for this product may be found. The icon must not be larger than 1MP.
downloadUrl - A url where the actual software the product represents may be downloaded. This link will be publicly available to users.
titles - A dictionary of localized product names. Each key represents an ISO 639-1 language code. You may specify a two letter country code after the language with a dash or an underscore (i.e. such as zh-tw, case insensitive). If that exact language id is not available for a particular task in the system, the system will attempt to use a more generic language id (i.e. for example, if es-CO is not available, then the system will try to use es). If the region agnostic language id is also not available, en (English) will be used. At least one key-value pair must be present, preferably in English.
'''

@dataclass
class ProductFormat:
    example: str
    prefix: str
    length: Dict[str, int]

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProductFormat':
        return cls(
            example=data['example'],
            prefix=data['prefix'],
            length=data['length']
        )

@dataclass
class Product:
    id: str
    creationDate: Optional[int] = None
    iss: Optional[str] = None
    format: Optional[Dict[str, Any]] = None
    version: Optional[str] = None
    platforms: Optional[List[str]] = None
    picture: Optional[str] = None
    downloadUrl: Optional[str] = None
    titles: Optional[Dict[str, str]] =None
    
    def __init__(self, data: Dict[str, Any] = None): 
        if(data is not None): 
            self.from_dict(data)
    def from_dict(self, data: Dict[str, Any]) -> None:
        for k,v in data.items(): 
            setattr(self, k, v) 
    def to_dict(self) -> Dict[str, Any]:
        # Using dataclasses.asdict() to properly handle nested structures
        return {
            key: value 
            for key, value in asdict(self).items() 
            if value is not None  # Optionally exclude None values
        }

class CloudZooClient: 
    # BASE_URL = "https://cloudzoo.rhino3d.com/v1"

    def __init__(self, issuer_id: str, issuer_secret: str):
        self.auth_header = self.create_auth_header(issuer_id, issuer_secret)
        self.base_url = Config.BASE_URL

    def create_auth_header(self, issuer_id: str, issuer_secret: str):
        auth_string = f"{issuer_id}:{issuer_secret}"
        base64_encoded = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        return {'Authorization': f"Basic {base64_encoded}"}


    def _handle_response(self, response: requests.Response) -> Dict:
        """Handle API response and raise appropriate exceptions."""
        if response.ok:
            return response.json()
        
        if 400 <= response.status_code < 500:
            error_data = response.json()
            raise Exception(
                f"API Error: {error_data.get('Error')}\n"
                f"Description: {error_data.get('Description')}\n"
                f"Details: {error_data.get('Details')}"
            )
        raise Exception(f"Server Error: Status code {response.status_code}")
    

    def create_product(self, product: Product) -> Dict:
        url = f"{self.BASE_URL}/product"
        response = requests.post(url,headers={
                **self.auth_header,
                "Content-Type": "application/json"
            },
            json=product.__dict__)
        return self._handle_response(response)
    
    
    def update_product(self, product_id: UUID, updates: Dict) -> Dict:
        """Update an existing product in Cloud Zoo."""
        url = f"{self.BASE_URL}/product/{str(product_id).lower()}"
        
        response = requests.put(
            url,
            headers={
                **self.auth_header,
                "Content-Type": "application/json"
            },
            json=updates
        )
        
        return self._handle_response(response)
    
    def get_product(self, product_id: UUID) -> Dict:
        url = f"{self.BASE_URL}/product/{str(product_id).lower()}"
        response = requests.get(url, headers=self.auth_header)
        return self._handle_response(response)
    
cz = CloudZooClient(issuer_id=Config.ISSUER_ID, issuer_secret=Config.ISSUER_SECRET)

def handle_error(f): 
    """Handle errors decorator."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try: 
            return f(*args, **kwargs)
        except Exception as e: 
            return jsonify({
                "error": str(e),
                "status": "f{e}, status 500"
            })
        
    return wrapper 

@app.route('/api/v1/product', methods=['POST'])
@handle_error 
def create_product(): 
    body = request.get_json() 
    try: 
        product = Product(body) 
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        },500)
    res = cz.create_product(product)
    return jsonify({"data":res, "status": "Product created successfully"})



@app.route('/api/v1/product/<product_id>',methods=['PUT'])
@handle_error 
def update_product(product_id:str): 
    """Update product."""
    try: 
        product_id = UUID(product_id.lower())
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"}) 
    body = request.get_json()
    result = cz.update_product(product_id, body) 
    return jsonify({"data":result, "status": "Product updated successfully"}) 

@app.route('/api/v1/product/<product_id>', methods=['GET'])
@handle_error 
def get_product(product_id:str): 
    try: 
        product_id = UUID(product_id.lower())
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"}) 
    res = cz.get_product(product_id)
    return jsonify({"data":res, "status": "Product fetched successfully"})   

if __name__ == "__main__": 
    app.run(debug=Config.DEBUG, port=Config.PORT)



