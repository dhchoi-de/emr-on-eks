import os
import json

import pytesseract
from pdf2image import convert_from_path
from tqdm import tqdm
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.types import ArrayType, StructType, StructField, StringType, IntegerType

# Spark Session 초기화 (S3 접근 설정 추가)
aws_access_key = os.environ['ACCESS_KEY']
aws_secret_access_key = os.environ['SECRET_ACCESS_KEY']
bucket = os.environ['BUCKET']

spark = SparkSession.builder \
    .appName("PDF OCR with Spark on EMR on EKS") \
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.2.0,com.amazonaws:aws-java-sdk:1.11.1012") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.access.key", f"{aws_access_key}") \
    .config("spark.hadoop.fs.s3a.secret.key", f"{aws_secret_access_key}") \
    .getOrCreate()

# PDF를 S3에서 읽어오는 함수
def get_pdf_paths(s3_bucket_uri):
    paths = spark.sparkContext._jvm.org.apache.hadoop.fs.FileSystem.get(
        spark._jsc.hadoopConfiguration()
    ).listStatus(
        spark._jsc.hadoopConfiguration().makeQualified(
            spark._jsc.hadoopConfiguration().getUri().resolve(s3_bucket_uri)
        )
    )
    return spark.createDataFrame(
        [(f.getPath().toString(),) for f in paths if f.getPath().toString().endswith('.pdf')],
        ["path"]
    )

def convert_pdf(image_path: str):
    images = convert_from_path(image_path)
    return images

def image_to_string(image):
    text = pytesseract.image_to_string(image, lang='kor', config=r'--oem 3 --psm 6')
    return json.dumps(text, ensure_ascii=False)

image_to_string_udf = udf(image_to_string, StringType())

def run_ocr_spark(s3_bucket_uri):
    pdf_paths_df = get_pdf_paths(s3_bucket_uri)
    def process_pdf(pdf_path):
        images = convert_pdf(pdf_path)
        pages = []
        for page, image in enumerate(tqdm(images)):
            text = image_to_string(image)
            pages.append({
                'page': page,
                'name': os.path.basename(pdf_path),
                'ocr': text
            })
        return pages

    process_pdf_udf = udf(process_pdf, ArrayType(StructType([
        StructField("page", IntegerType()),
        StructField("name", StringType()),
        StructField("ocr", StringType())
    ])))
    
    result_df = pdf_paths_df.withColumn("pages", process_pdf_udf(col("path"))).select("path", "pages")
    result_df = result_df.select(
        "path",
        col("pages.page").alias("page"),
        col("pages.name").alias("name"),
        col("pages.ocr").alias("ocr")
    )
    
    return result_df

def run():
    s3_bucket_uri = f"s3a://{bucket}"
    result = run_ocr_spark(s3_bucket_uri)
    result.write.csv(f"s3a://{bucket}", header=True, mode="overwrite")
    spark.stop()

if __name__ == "__main__":
    run()