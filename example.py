"""
Epycor - Python package for Epicor/Kinetic ERP REST API use

Example usage:

>>> from Epycor.client import ERP
>>> foo = ERP(server_root, instance_name, api_key, company_ID)
>>> foo.Login(userid, pwd)
>>> bar = foo.Erp.BO.VendorSvc.GetByVendID(vendorID="DIGCO").json()['returnObj']
>>> bar['Vendor'][0]['Name']
'Digi-Key Corporation'
>>> foo.Logout()
"""


import json
from Epycor.client import ERP
from getpass import getpass, getuser
from pprint import pprint


if __name__ == '__main__':
    welcome = """This is a basic Epicor command shell made using Python.

Right now it just displays the company information for the selected company.
"""
    print(welcome)

    server_root = input("Server root URL? ")
    instance_name = input("Instance name? ")
    api_key = input("API key? ")
    company_ID = input("Company ID? ")

    our_ERP = ERP(server_root, instance_name, api_key, company_ID)

    current_user = getuser()
    userid = input(f"User ID? ({current_user}) ") or current_user
    pwd = getpass("Password? ")

    our_ERP.Login(userid, pwd)
    print(f"Logged in as {userid}.")

    our_company = our_ERP.Ice.BO.CompanySvc.GetByID(company=company_ID).json()
    pprint(our_company)

    our_ERP.Logout()
