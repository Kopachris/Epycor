# Epycor
Simple Python package for Epicor/Kinetic ERP REST API use.

## Dependencies
Epycor's only major dependency is [`requests`](https://requests.readthedocs.io/en/latest/).

I've only tested Epycor on Python 3.11.

## Introduction
The `ERP` is the main class through which Epicor is interacted with. Each
API request has several parts:

    ERP.Schema.Namespace.Service.Method

In this way, the Service object is responsible for using a decorated function
to create the endpoint URL and request for the method call.

To connect to your Epicor instance, the constructor for `ERP` takes the following
arguments. Claiming a specific license is optional.
* EpicorServer
* ERPInstance
* APIKey
* Company
* ClaimLicense = false
* LicenseType = Epycor.licenses.Default

```python
from Epycor.client import ERP
our_ERP = ERP("https://erp.example.com", "E10Demo", "apikey", "EPIC06")
```

Any of the URL parts can also be identified using subscript notation, which is
useful when the name of a service you're trying to use has a hyphen in it, as with
many BAQ IDs.

```python
our_users = our_ERP.Erp.Baq['zCRM-Users'].Data().json()
```

## Business Activity Queries
To use a BAQ, use Namespace "Baq" or "BaqSvc" with any Schema (examples will use
"Erp" for the schema). The Service will be the name of the BAQ, and the Method will 
be "Data" or "GetNew". For BAQs, parameters are passed to the method as kwargs. To 
use updatable BAQs, pass a single changed row to the Data method as a dict, "ds". 
You can also call the GetNew method to get an empty row.

```python
resp = our_ERP.Erp.Baq.OrdersDashHed.Data(BeginDate='01/01/2024', EndDate='01/31/2024')
print(resp.json())
new_row = our_ERP.Erp.Baq.CustomScheduler.GetNew().json()['value'][0]
new_row['JobHead_StartDate'] = '07/01/2024'
resp = our_ERP.Erp.Baq.CustomScheduler.Data(ds=new_row)
```

## Epicor Function Libraries
To use an Epicor Functions Library (aka EFX), use Namespace "Efx" with any Schema.
The Service will be the name of the library, and the Method will be the function
within the library to call.

```python
resp = our_ERP.Erp.Efx.ExampleEfxLib.ExampleFunc(someparam="foo")
print(resp.json())
```

## Shortcuts
It can be helpful to create shortcut aliases for specific API services that you will
be using often.

```python
baq = our_ERP.Erp.Baq
customers = baq['zCRM-Customers'].Data().json()

our_efx = our_ERP.Erp.Efx.ExampleEfxLib
resp = our_efx.Function1(someparam="foo", otherparam="bar")
resp.raise_for_status()     # will raise if not HTTP 200
our_efx.Function2().raise_for_status()      # if we don't care about returned data

cust_svc = our_ERP.Erp.BO.CustomerSvc
cust_ds = cust_svc.GetNewCustomer(ds=dict()).json()
cust_ds['Customer'][0]['Name'] = "Example Manufacturing LLC"
cust_ds['Customer'][0]['Address1'] = "123 N Umber St."
cust_ds['Customer'][0]['City'] = "Portland"
cust_ds['Customer'][0]['State'] = "OR"
cust_ds['Customer'][0]['Zip'] = "97210"
cust_ds['Customer'][0]['Country'] = "US"
resp = cust_svc.Update(ds=cust_ds)
resp.raise_for_status()
cust_ds = resp.json()
```
