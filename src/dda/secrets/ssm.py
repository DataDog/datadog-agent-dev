def fetch_secret(name: str) -> str:
    import boto3

    ssm = boto3.client("ssm", region_name="us-east-1")
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]
