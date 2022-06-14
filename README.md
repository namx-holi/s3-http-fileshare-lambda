# s3-http-fileshare-lambda
Code for setting up access to files within an S3 bucket as though they are an Apache fileshare, using a lambda function on AWS


## Setup
Create a lambda function using Python3.8+ in AWS with an API gateway and S3 read permissions.

Replace the `lambda_function.py` code with the one in this repo.

Add environment variables:
	- S3_BUCKET_NAME = the name of the bucket mp3s are stored in
	- S3_REGION_NAME = the region the bucket is located in
	- S3_STORE_PATH  = the directory we are using to share in the bucket, e.g. "public" or empty for root

In the `nginx-site.conf`, replace instances of `example.com` with your domain, and the proxy_pass directive link to the url of your API gateway for the lambda function. Also either comment out ssl lines or replace them with relevant lines for your setup.


## Notes
Remove the default nginx index.html file, as nginx will try to redirect
to that by default when the root directive is not set.
https://stackoverflow.com/a/59501902
