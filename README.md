# s3-http-fileshare-lambda
Code for setting up access to files within an S3 bucket as though they are an Apache fileshare, using a lambda function on AWS


## NOTES
Remove the default nginx index.html file, as nginx will try to redirect
to that by default when the root directive is not set.
https://stackoverflow.com/a/59501902
