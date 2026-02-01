#!/usr/bin/env python3

# $ python3 ./bedrock_chat.py --quiet
# You: when Feinman was born?
# <reasoning>We have user asking: "when Feinman was born?" Likely referring to Richard Feynman, the physicist. The spelling "Feinman"? Could be a typo. So answer: Richard Feynman was born May 11, 1918. Provide context. Also mention other Feinmans? There's possibly a "Feinman" like "Michael Feinman"? But likely Richard Feynman. Provide birth date and location. Provide citations. Answer concisely.</reasoning>Richard Feynman – the Nobel‑winning American theoretical physicist – was born on **May 11 1918** in **Queens, New York City**, USA. (He later passed away on February 15 1988.)
# You: exit
#
# $ python3 ./bedrock_chat.py --quiet --local
# Using LOCAL Ollama model: gpt-oss:120b-cloud
# Type 'exit' or Ctrl+C to quit.

# You: when Feinman was born?
# AI: Richard Feynman – the legendary American physicist best known for his work in quantum electrodynamics, his vivid teaching style, and his popular science books – was born on **May 11 1918** in Queens, New York City, USA.

# You:

import sys
import json
import re
import requests
import boto3
from botocore.exceptions import ClientError

LOCAL_OLLAMA_URL = "http://localhost:11434/api/chat"
LOCAL_MODEL = "gpt-oss:120b-cloud"

# ---------------------------------------------------------
# CLEAN OUTPUT FOR TERMINAL
# ---------------------------------------------------------
def clean_console_text(text):
    text = re.sub(r"\\\[(.*?)\\\]", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\\\((.*?)\\\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------
# OLLAMA RESPONSE EXTRACTION
# ---------------------------------------------------------
def extract_ollama_output(data):
    if "message" in data and "content" in data["message"]:
        return data["message"]["content"]
    if "response" in data:
        return data["response"]
    return json.dumps(data)


# ---------------------------------------------------------
# LOCAL OLLAMA CHAT
# ---------------------------------------------------------
def chat_local():
    print(f"Using LOCAL Ollama model: {LOCAL_MODEL}")
    print("Type 'exit' or Ctrl+C to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("Bye!")
                break

            payload = {
                "model": LOCAL_MODEL,
                "messages": [
                    {"role": "user", "content": user_input}
                ],
                "stream": False
            }

            response = requests.post(LOCAL_OLLAMA_URL, json=payload)
            data = response.json()

            raw_output = extract_ollama_output(data)
            output = clean_console_text(raw_output)

            print(f"AI: {output}\n")

        except KeyboardInterrupt:
            print("\nBye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")


# ---------------------------------------------------------
# REMOTE BEDROCK CHAT WITH A2 FALLBACK
# ---------------------------------------------------------
def chat_bedrock(verbose=False, quiet=False):
    if not quiet:
        print("Using REMOTE Bedrock models")
        print("Using AWS credentials from ~/.aws")
        print("Type 'exit' or Ctrl+C to quit.\n")

    bedrock = boto3.client("bedrock-runtime")
    bedrock_mgmt = boto3.client("bedrock")

    # Discover available models
    try:
        model_list = bedrock_mgmt.list_foundation_models()["modelSummaries"]
        all_models = [m["modelId"] for m in model_list]
    except Exception as e:
        print(f"Error discovering Bedrock models: {e}")
        return

    # Filter by A2 priority families
    claude = [m for m in all_models if m.startswith("anthropic.claude")]
    gptoss = [m for m in all_models if m.startswith("openai.gpt-oss")]
    llama = [m for m in all_models if m.startswith("meta.llama3")]

    fallback_order = claude + gptoss + llama

    if not fallback_order:
        print("No supported chat models available in this AWS region/account.")
        return

    if verbose and not quiet:
        print("Fallback order:")
        for m in fallback_order:
            print(" -", m)
        print()

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                if not quiet:
                    print("Bye!")
                break

            # Try each model in A2 order
            for model_id in fallback_order:
                if verbose and not quiet:
                    print(f"Trying {model_id}...")

                # Build correct payload per family
                if model_id.startswith("anthropic.claude"):
                    payload = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 300,
                        "messages": [{"role": "user", "content": user_input}]
                    }

                elif model_id.startswith("openai.gpt-oss"):
                    payload = {
                        "messages": [{"role": "user", "content": user_input}]
                    }

                elif model_id.startswith("meta.llama3"):
                    payload = {
                        "prompt": user_input,
                        "max_gen_len": 300
                    }

                else:
                    continue  # shouldn't happen

                # Attempt invocation
                try:
                    response = bedrock.invoke_model(
                        modelId=model_id,
                        body=json.dumps(payload)
                    )

                    body = json.loads(response["body"].read())

                    # Extract output for all supported model families
                    if "output_text" in body:
                        raw_output = body["output_text"]

                    elif "generation" in body:
                        raw_output = body["generation"]

                    elif "message" in body and "content" in body["message"]:
                        raw_output = body["message"]["content"]

                    elif "choices" in body and body["choices"]:
                        # GPT‑OSS / OpenAI‑style
                        choice = body["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            raw_output = choice["message"]["content"]
                        else:
                            raw_output = json.dumps(body)

                    else:
                        raw_output = json.dumps(body)

                    #raw_output = (
                    #    body.get("output_text")
                    #    or body.get("generation")
                    #    or body.get("message", {}).get("content")
                    #    or json.dumps(body)
                    #)

                    if raw_output:
                        output = clean_console_text(raw_output)
                        if not quiet:
                            print(f"AI ({model_id}): {output}\n")
                        else:
                            print(output)
                        break

                except ClientError as ce:
                    if verbose and not quiet:
                        print(f"Model {model_id} failed: {ce.response['Error']['Message']}")
                    continue

                except Exception as e:
                    if verbose and not quiet:
                        print(f"Model {model_id} error: {e}")
                    continue

            else:
                print("No Bedrock model returned a valid answer.\n")

        except KeyboardInterrupt:
            if not quiet:
                print("\nBye!")
            break
        except Exception as e:
            print(f"Error: {e}\n")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    args = sys.argv[1:]
    local = "--local" in args
    verbose = "--verbose" in args
    quiet = "--quiet" in args

    if local:
        chat_local()
    else:
        chat_bedrock(verbose=verbose, quiet=quiet)


if __name__ == "__main__":
    main()
