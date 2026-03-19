#!/usr/bin/env bash
if [ $# -lt 1 ]; then
    echo "Usage: sh $0 <original_text>"
    echo "Note: Please modify the API_KEY variable in the script using your own deepseek API key."
    exit 0
fi
API_KEY="sk-XXXXXXXXXXXXXXXXXXXXXXXXX"

content="$@"
data_body="{ \"model\": \"deepseek-chat\", \"messages\": [ {\"role\": \"system\", \"content\": \"Translate to English if Chinese, else to Chinese. For single words or short phrases, include brief usage notes and grammar. For sentences or longer text, output translation only\"}, {\"role\": \"user\", \"content\": \"${content}\"} ], \"stream\": false }"
curl -s https://api.deepseek.com/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer ${API_KEY}" -d "$(echo ${data_body} | jq)" | jq -r '"\(.choices[0].message.content)\nTotal_token: \(.usage.total_tokens)"'
