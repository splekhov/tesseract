#!/bin/bash

APIKEY="$1"

if [ -z "$APIKEY" ]; then
  echo "Usage: $0 <apikey>"
  exit 1
fi

ES_URL="https://_your_elastic_endpoint_:443"
INDEX="_your_index_name*"

QUERY='{
  "query": {
    "bool": {
      "must": [
        { "match_phrase": { "message": "Error creating document from api [400 Bad Request] during [POST]" } },
        {
          "range": {
            "@timestamp": {
              "gte": "now-30d/d",
              "lte": "now/d"
            }
          }
        }
      ]
    }
  }
}'

# -------------------------
# Initial search
# -------------------------
RESPONSE=$(curl -s -X POST "$ES_URL/$INDEX/_search?scroll=2m" \
  -H "Content-Type: application/json" \
  -H "Authorization: ApiKey $APIKEY" \
  -d "$QUERY")

# Check for ES error
if echo "$RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
  echo "Elasticsearch error:"
  echo "$RESPONSE" | jq '.error'
  exit 1
fi

SCROLL_ID=$(echo "$RESPONSE" | jq -r '._scroll_id // empty')

# Stop if scroll_id missing
if [ -z "$SCROLL_ID" ]; then
  echo "No scroll_id returned. Exiting."
  exit 0
fi

# Print first batch
echo "$RESPONSE" | jq -r '
  .hits.hits[]? |
  [
    ._source["process-id"],
    ._source["process-instance"],
    ._source["process-version"],
    ._source["@timestamp"],
    ._source["message"]
  ] | @csv' | tr -d '"'

# -------------------------
# Scroll loop
# -------------------------
while true; do

  RESPONSE=$(curl -s -X POST "$ES_URL/_search/scroll" \
    -H "Content-Type: application/json" \
    -H "Authorization: ApiKey $APIKEY" \
    -d "{\"scroll\":\"2m\",\"scroll_id\":\"$SCROLL_ID\"}")

  # Stop on ES error
  if echo "$RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
    echo "Elasticsearch scroll error:"
    echo "$RESPONSE" | jq '.error'
    exit 1
  fi

  # Extract hits count safely
  HITS=$(echo "$RESPONSE" | jq -r '.hits.hits | length // 0')

  # If HITS is empty or non-numeric, force to 0
  case "$HITS" in
    ''|*[!0-9]*) HITS=0 ;;
  esac

  # Stop when no more hits
  if [ "$HITS" -eq 0 ]; then
    break
  fi

  # Print results
  echo "$RESPONSE" | jq -r '
    .hits.hits[]? |
    [
      ._source["process-id"],
      ._source["process-instance"],
      ._source["process-version"],
      ._source["@timestamp"],
      ._source["message"]
    ] | @csv' | tr -d '"'

  # Update scroll_id
  SCROLL_ID=$(echo "$RESPONSE" | jq -r '._scroll_id // empty')

  if [ -z "$SCROLL_ID" ]; then
    echo "Scroll ended (no scroll_id)."
    break
  fi

done

