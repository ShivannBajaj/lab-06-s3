#!/bin/bash
set -euo pipefail

# Validate arguments
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <book_url> <bucket_name> <expiration_seconds>"
    exit 1
fi

BOOK_URL="$1"
BUCKET="$2"
EXPIRATION="$3"

# Extract filename from URL
FILENAME=$(basename "$BOOK_URL")
mkdir -p books
LOCAL_PATH="books/$FILENAME"

# Download the book with curl if not already present
if [ ! -f "$LOCAL_PATH" ]; then
    echo "Downloading $BOOK_URL..."
    curl -s -o "$LOCAL_PATH" "$BOOK_URL"
fi

# Create private bucket if it doesn't exist
if ! aws s3 ls "s3://$BUCKET" > /dev/null 2>&1; then
    echo "Creating private bucket $BUCKET..."
    aws s3 mb "s3://$BUCKET" --region us-east-1
fi

# Upload file privately with correct content type
echo "Uploading $FILENAME to s3://$BUCKET/$FILENAME..."
aws s3 cp "$LOCAL_PATH" "s3://$BUCKET/$FILENAME" --content-type "text/plain; charset=utf-8"

# Generate and print presigned URL
echo "Generating presigned URL (expires in $EXPIRATION seconds):"
aws s3 presign "s3://$BUCKET/$FILENAME" --expires-in "$EXPIRATION"
