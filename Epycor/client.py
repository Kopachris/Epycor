"""
Main ERP client classes.

The ERP is the main class through which Epicor is interacted with. Each
API request has several parts:

    ERP.Schema.Namespace.Service.Method

In this way, the Service object is responsible for using a decorated function
to create the endpoint URL and request for the method call.

To use an Epicor Functions Library (aka EFX), use Namespace "Efx" with any Schema.
The Service will be the name of the library, and the Method will be the function
within the library to call.

To use a BAQ, use Namespace "Baq" or "BaqSvc" with any Schema. The Service will be
the name of the BAQ, and the Method will be "Data" or "GetNew". For BAQs, parameters
are passed to the method as kwargs. To use updatable BAQs, pass a single changed row
to the Data method as a dict, "ds". You can also call the GetNew method to get an
empty row. TODO: clean up the GetNew call a bit

e.g.,
    resp = our_ERP.Erp.Baq.OrdersDashHed.Data(BeginDate='01/01/2024', EndDate='01/31/2024')
    print(resp.json())
    new_row = our_ERP.Erp.Baq.CustomScheduler.GetNew().json()['value'][0]
    new_row['JobHead_StartDate'] = '07/01/2024'
    resp = our_ERP.Erp.Baq.CustomScheduler.Data(ds=new_row)

In cases where one of the segments of the API call contains a special character that can't
be used in an object name in Python, such as a BAQ with a hyphen in its name, you can
instead use subscript notation, e.g.,

    our_users = our_ERP.Erp.Baq['zCRM-Users'].Data().json()

You can actually use the subscript notation wherever you like, but I had to add it for
those pesky BAQs with hyphens in their names.

BSD 3-Clause License

Copyright (c) 2024, Christopher Koch

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from . import licenses
import json
import requests


class ERP(object):
    def __init__(self, EpicorServer: str, ERPInstance: str, APIKey: str, Company: str, ClaimLicense: bool = False, LicenseType: str = licenses.Default):
        self._EpicorServer = EpicorServer
        self._ERPInstance = ERPInstance
        self.APIKey = APIKey
        self.CurrentCompany = Company
        self.ClaimLicense = ClaimLicense

        if LicenseType not in licenses.valid_licenses:
            raise ValueError(f"Given unknown/invalid license type: {LicenseType}")
        self._LicenseType = LicenseType

        self._is_open = False
        self._SessionID = None
        self.username = None
        self.password = None

    @property
    def IsOpen(self):
        """Current status of the connection"""
        return self._is_open

    @property
    def SessionID(self):
        """Current session ID to use for these API calls"""
        return self._SessionID

    @property
    def LicenseType(self):
        """The license type GUID to use for these API calls"""
        return self._LicenseType

    @LicenseType.setter
    def LicenseType(self, new_value: str):
        if new_value not in licenses.valid_licenses:
            raise ValueError(f"Given unknown/invalid license type: {new_value}")
        self._LicenseType = new_value

    @property
    def EpicorServer(self):
        """The base server URL for this connection"""
        return self._EpicorServer

    @EpicorServer.setter
    def EpicorServer(self, new_value: str):
        if not new_value.lower().startswith("https://"):
            # must use https
            raise ValueError(f"EpicorServer URL must start with 'https://'. Got `{new_value}`")

        if self.IsOpen:
            self.Close()
        self._EpicorServer = new_value

    @property
    def ERPInstance(self):
        """The ERP instance for this connection, e.g. E10Demo, E10Live"""
        return self._ERPInstance

    @ERPInstance.setter
    def ERPInstance(self, new_value: str):
        if self.IsOpen:
            self.Close()
        self._ERPInstance = new_value

    @property
    def BaseURL(self):
        return f"{self.EpicorServer}/{self.ERPInstance}/api/v2/odata/{self.CurrentCompany}"

    @property
    def EfxURL(self):
        return f"{self.EpicorServer}/{self.ERPInstance}/api/v2/efx/{self.CurrentCompany}"

    @property
    def RequestHeaders(self):
        headers = dict()
        headers["x-api-key"] = self.APIKey
        if self.ClaimLicense:
            lic = {"ClaimedLicense": self.LicenseType}
            if self.SessionID:
                lic["SessionID"] = self.SessionID
            headers["License"] = json.dumps(lic)
        return headers

    def Close(self):
        """Close this API connection"""
        if self.SessionID:
            self.Logout()
        self._is_open = False

    def Login(self, username, password):
        """Set authentication info and get a session ID"""
        self.username = username
        self.password = password

        resp = self.Ice.Lib.SessionModSvc.Login()
        resp.raise_for_status()
        self._SessionID = resp.json()["returnObj"]
        self._is_open = True

    def Logout(self):
        resp = self.Ice.Lib.SessionModSvc.Logout()
        resp.raise_for_status()
        self._SessionID = None

    def __getattr__(self, name):
        return EpiSchema(self, name)

    __getitem__ = __getattr__


class EpiSchema(object):
    def __init__(self, instance: ERP, schema: str):
        self._schema = None
        self.schema = schema
        self._instance = instance

    @property
    def schema(self):
        """Schema to use for this lookup, Ice or Erp"""
        return self._schema

    @schema.setter
    def schema(self, new_value: str):
        if new_value.upper() not in ('ERP', 'ICE'):
            raise ValueError(f"Unknown Epicor schema: {new_value}")
        self._schema = new_value

    @property
    def instance(self):
        return self._instance

    def __getattr__(self, name):
        return EpiNamespace(self, name)

    def __str__(self):
        return self.schema

    __getitem__ = __getattr__


class EpiNamespace(object):
    def __init__(self, schema: EpiSchema, namespace: str):
        self._ns = None
        self.namespace = namespace
        self._schema = schema

    @property
    def namespace(self):
        """Namespace to use for this lookup"""
        return self._ns

    @namespace.setter
    def namespace(self, new_value):
        if new_value.upper() not in ('BO', 'LIB', 'PROC', 'RPT', 'EFX', 'BAQ'):
            raise ValueError(f"Unknown Epicor namespace: {new_value}")
        self._ns = new_value

    @property
    def schema(self):
        """Schema to use for this lookup"""
        return self._schema

    def __getattr__(self, name):
        return EpiService(self.schema, self, name)

    def __str__(self):
        return f"{self.schema}.{self.namespace}"

    __getitem__ = __getattr__


class EpiService(object):
    """This is the namespace and service whose method we're trying to call.
    e.g.,
    BO.CustomerSvc
    BO.MenuSvc
    Lib.FileStoreSvc
    Rpt.ARInvFormSvc
    Rpt.MenuSecuritySvc
    Efx.MyFunctionLibrary
    Baq.MyCustomQuery

    In the cases of BO, Lib, and Rpt namespaces, the schema (Ice or Erp) is important.
    In the cases of EFx and Baq namespaces, the schema is not passed through to the URL
    and is not checked. I'd recommend just sticking with Erp, though. We might change this in the future.

    As the resultant URLs aren't actually case-sensitive, technically neither are these names.

    """
    def __init__(self, schema: EpiSchema, namespace: EpiNamespace, service: str):
        self._schema = schema
        self._namespace = namespace
        self._svc = service

    @property
    def schema(self):
        return self._schema

    @property
    def namespace(self):
        return self._namespace

    @property
    def svc(self):
        return self._svc

    def __getattr__(self, name):
        return EpiMethod(self.schema.instance, self, name)

    def __str__(self):
        return f"{self.namespace}.{self.svc}"

    __getitem__ = __getattr__


def EpiMethod(instance: ERP, service: EpiService, method: str):
    def EpiMethodCall(**kwargs):
        our_ns = service.namespace.namespace.upper()
        if our_ns == 'EFX':
            req_url = f"{instance.EfxURL}/{service.svc}/{method}"
        elif our_ns == 'BAQ' or our_ns == 'BAQSVC':
            req_url = f"{instance.BaseURL}/BaqSvc/{service.svc}/{method}"
        else:
            req_url = f"{instance.BaseURL}/{service}/{method}"

        if not instance.username or not instance.password:
            raise Exception("ERP instance has no username or password!")
        if not instance.CurrentCompany:
            raise Exception("ERP instance has no company set!")
        auth = (instance.username, instance.password)

        if method.lower() in ('getbyid', 'getlist', 'getrows', 'getbysysrowid', 'getbysysrowids'):
            # POST requests for these endpoints are deprecated, replaced by GET requests
            resp = requests.get(req_url, params=kwargs, headers=instance.RequestHeaders, auth=auth)
        elif our_ns == 'BAQ' or our_ns == 'BAQSVC':
            if method.lower() == 'data' and 'ds' in kwargs.keys():
                # to distinguish an updatable BAQ call
                resp = requests.patch(req_url, json=kwargs['ds'], headers=instance.RequestHeaders, auth=auth)
            else:
                resp = requests.get(req_url, params=kwargs, headers=instance.RequestHeaders, auth=auth)
        else:
            resp = requests.post(req_url, json=kwargs, headers=instance.RequestHeaders, auth=auth)
        return resp
    return EpiMethodCall
