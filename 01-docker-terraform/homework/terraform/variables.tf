variable "credentials" {
  description = "My Credentials"
  default     = "../../../de-course-484302-f4fb526ccbf2.json"
  #ex: if you have a directory where this file is called keys with your service account json file
  #saved there as my-creds.json you could use default = "./keys/my-creds.json"
}


variable "project" {
  description = "Project"
  default     = "de-course-484302"
}

variable "region" {
  description = "Region"
  #Update the below to your desired region
  default     = "asia-southeast2"
}

variable "location" {
  description = "Project Location"
  #Update the below to your desired location
  default     = "asia-southeast2"
}

variable "gcs_bucket_name" {
  description = "My Storage Bucket Name"
  #Update the below to a unique bucket name
  default     = "bucket-terraform-course"
}

variable "gcs_storage_class" {
  description = "Bucket Storage Class"
  default     = "STANDARD"
}

variable "bq_dataset_name" {
  description = "My BigQuery Dataset Name"
  #Update the below to what you want your dataset to be called
  default     = "demo_dataset"
}