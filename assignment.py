import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
from typing import Dict, Any


class ParseAvailRequest:
    def __init__(self):
        # Constants as per the logic
        self.allowed_currencies = {"EUR", "USD", "GBP"}
        self.allowed_nationalities = {"US", "GB", "CA"}
        self.allowed_market = {"US", "GB", "CA", "ES"}
        self.var_filters_cg = {"en", "fr", "de", "es"}
        self.allowed_room_count = 5
        # Default values
        self.default_language = "en"
        self.default_currency = "EUR"
        self.default_nationality = "US"
        self.default_market = "ES"
        self.allowed_hotel_count = 10
        self.options_quota = 20
        self.max_child_age = 5
        self.allowed_room_guest_count = 5

        self.price = {
            "net": 132.42,  # Sample net price
            "currency": "USD",  # Sample currency
        }

    def validate_destination(self, search_type, avail_destinations):
        if search_type == "Single" and len(avail_destinations) != 1:
            raise ValueError(
                "If SearchType is 'Single', there must be exactly one destination."
            )
        if (
            search_type == "Multiple"
            and len(avail_destinations) > self.allowed_hotel_count
        ):
            raise ValueError(
                f"If SearchType is 'Multiple', there can be a maximum of {ALLOWED_HOTEL_COUNT} destinations."
            )

    def validate_user(self, password, username, company_id):
        if not (password and username and company_id):
            raise ValueError(
                "Missing required parameters: password, username, or CompanyID."
            )

    def validate_date(start_date, end_date):
        # Date validation
        if start_date <= datetime.today() + timedelta(days=2):
            raise ValueError("Start date must be at least 2 days after today.")
        if (end_date - start_date).days < 3:
            raise ValueError("Stay duration must be at least 3 nights.")

    def validate_options_quota(self, options_quota):
        if not options_quota:
            options_quota = self.options_quota
        if options_quota > 50:
            raise ValueError("OptionsQuota must be no greater than 50.")

    def validate_language_code(self, language_code):
        if language_code not in self.var_filters_cg:
            raise ValueError(f"Invalid language code: {language_code}")

    def calculate_selling_price(
        self, net_price: float, markup_percentage: float
    ) -> float:
        """Calculate selling price based on markup percentage"""
        return net_price * (1 + markup_percentage / 100)

    def validate_room_count(self, count):
        if count > self.allowed_room_count:
            raise ValueError(
                f"Number of rooms cannot exceed {self.allowed_room_count}."
            )

    def parse(self, xml_string: str):
        # Parse the XML
        root = ET.fromstring(xml_string)

        # Extract language
        language_code = root.find(".//source/languageCode")
        language_code = (
            language_code.text
            if language_code is not None
            else DEFAULT_LANGUAGE
        )
        # Validate language
        self.validate_language_code(language_code)

        # Extract parameters (username, password, CompanyID)
        parameters = root.find(".//Configuration/Parameters/Parameter")
        password = parameters.get("password")
        username = parameters.get("username")
        company_id = parameters.get("CompanyID")
        # Validate user Details
        self.validate_user(password, username, company_id)

        # Extract and Validate destinations
        search_type = root.find(".//SearchType").text
        avail_destinations = root.findall(".//AvailDestinations")
        self.validate_destination(search_type, avail_destinations)

        # Extract and Validate Dates
        start_date = root.find(".//StartDate").text
        end_date = root.find(".//EndDate").text
        start_date = datetime.strptime(start_date, "%d/%m/%Y")
        end_date = datetime.strptime(end_date, "%d/%m/%Y")

        # Extract and validate Option Quota
        options_quota = root.find(".//optionsQuota").text
        options_quota = int(options_quota) if options_quota else None
        self.validate_options_quota(options_quota)

        # Extract currency, nationality and market
        currency = root.find(".//Currency").text
        currency = (
            currency
            if currency in self.allowed_currencies
            else self.default_currency
        )
        nationality = root.find(".//Nationality").text
        nationality = (
            nationality
            if nationality in self.allowed_nationalities
            else self.default_nationality
        )
        market = root.find(".//Market")
        market = market.text if market is not None else self.default_market

        # Extract room and passenger information
        paxes = root.findall(".//Paxes")
        self.validate_room_count(len(paxes))
        pax_data = []
        for paxes_block in paxes:
            pax_list = []
            for pax in paxes_block.findall(".//Pax"):
                age = int(pax.get("age", 0))  # Assuming `age` is an attribute
                pax_type = "Child" if age <= self.max_child_age else "Adult"
                pax_data.append({"age": age, "type": pax_type})

            # Validate the number of passengers per room
            if len(pax_data) > self.allowed_room_guest_count:
                raise ValueError(
                    f"Number of passengers in a room cannot exceed {self.allowed_room_guest_count}."
                )

            # Check for child validation (Children must have at least one accompanying adult)
            child_count = sum(1 for pax in pax_data if pax["type"] == "Child")
            adult_count = sum(1 for pax in pax_data if pax["type"] == "Adult")

        # Return data
        return {
            "language_code": language_code,
            "options_quota": options_quota,
            "password": password,
            "username": username,
            "company_id": company_id,
            "search_type": search_type,
            "start_date": start_date,
            "end_date": end_date,
            "currency": currency,
            "nationality": nationality,
            "market": market,
            "avail_destinations": avail_destinations,
            "paxes": paxes,
        }

    def generate_response(self, data: Dict[str, Any]) -> str:
        """Generate a JSON response based on the input data"""
        response = []
        id = 1
        for destination in data["avail_destinations"]:
            markup_percentage = 3.2
            selling_price = self.calculate_selling_price(
                self.price["net"], markup_percentage
            )
            # Build response object

            response_item = {
                "id": f"A#{id}",
                "hotelCodeSupplier": "39971881",  # Example hotel code
                "market": data["market"],
                "price": {
                    "minimumSellingPrice": None,
                    "currency": self.price["currency"],
                    "net": self.price["net"],
                    "selling_price": selling_price,
                    "selling_currency": data["currency"],
                    "markup": markup_percentage,
                    "exchange_rate": 1.0,  # Assuming no exchange rate for simplicity
                },
            }
            response.append(response_item)
            id += 1
        return json.dumps(response, indent=2)

    def main(self, xml_request: str) -> str:
        try:
            data = self.parse(xml_request)
            response = self.generate_response(data)
            return response
        except ValueError as e:
            return json.dumps({"error": str(e)})


xml_request = """<AvailRQ xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<timeoutMilliseconds>25000</timeoutMilliseconds>
<source>
<languageCode>en</languageCode>
</source>
<optionsQuota>20</optionsQuota>
<Configuration>
<Parameters>
<Parameter password="XXXXXXXXXX" username="YYYYYYYYY" CompanyID="123456"/>
</Parameters>
</Configuration>
<SearchType>Multiple</SearchType>
<StartDate>14/10/2024</StartDate>
<EndDate>16/10/2024</EndDate>
<Currency>USD</Currency>
<Nationality>US</Nationality>
<AvailDestinations></AvailDestinations>
<AvailDestinations></AvailDestinations>
<AvailDestinations></AvailDestinations>
<Paxes>
    <Pax age="10" />
    <Pax age="3" />
</Paxes>
<Paxes>
    <Pax age="35" />
    <Pax age="2" />
</Paxes>
</AvailRQ>"""


parse = ParseAvailRequest()
response = parse.main(xml_request)
print(response)
