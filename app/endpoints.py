from app.structures import Endpoint


ENDPOINTS: list[Endpoint] = [
    Endpoint(
        name="Persons Endpoint with BannerId Criteria",
        url="https://integrate.elluciancloud.com/api/persons",
        params={
            "criteria": {
                "credentials": [
                    {"type": "bannerId", "value": "M00251282"}
                ]
            }
        },
        needs_bearer_token=True,
    ),
    Endpoint(
        name="User Identity Profile from GUID",
        url="https://integrate.elluciancloud.com/api/user-identity-profiles",
        path_suffix="/88710f32-8ed6-4ad7-ad02-2458fdd0640f",
        needs_bearer_token=True,
    )]
