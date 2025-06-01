from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import os

# current_dir = os.path.dirname(os.path.abspath(__file__))  # ...\Desktop\bot
# parent_dir = os.path.dirname(current_dir)               # ...\Desktop

# checkpoint_path = os.path.join(parent_dir, "models/final_model1")
# tokenizer = AutoTokenizer.from_pretrained(checkpoint_path, local_files_only=True)
# model = AutoModelForTokenClassification.from_pretrained(checkpoint_path)

from pathlib import Path

checkpoint_path = Path(__file__).parent / "../models/final_model1"

tokenizer = AutoTokenizer.from_pretrained(checkpoint_path.resolve(), local_files_only=True, repo_type='model')

model = AutoModelForTokenClassification.from_pretrained(checkpoint_path, local_files_only=True, repo_type='model')

labels = model.config.id2label

def extract_entities(text):
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=-1)

    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    pred_tags = [labels[p.item()] for p in predictions[0]]

    final_tokens = []
    final_tags = []
    current_token = ""
    current_tag = ""

    for token, tag in zip(tokens, pred_tags):
        if token in ['[CLS]', '[SEP]']:
            continue
        if token.startswith("##"):
            current_token += token[2:]
        else:
            if current_token:
                final_tokens.append(current_token)
                final_tags.append(current_tag)
            current_token = token
            current_tag = tag

    if current_token:
        final_tokens.append(current_token)
        final_tags.append(current_tag)

    data = {
        "payer": "",
        "amount": "",
        "spending_category": "",
        "recipients": "",
        "note": ""
    }

    for token, tag in zip(final_tokens, final_tags):
        if tag == "O":
            continue
        tag_type = tag[2:].lower()
        if tag_type in data:
            if token not in data[tag_type]:
                data[tag_type] += token + " "

    for k in data:
        data[k] = data[k].strip()

    if data["amount"]:
        amt_text = data["amount"].lower().replace(",", "")
        if "k" in amt_text and "tr" in amt_text:
            parts = amt_text.split("tr")
            data["amount"] = int(float(parts[1].replace("k", "")) * 1000 + float(parts[0]) * 1000000)
        elif "k" in amt_text:
            data["amount"] = int(float(amt_text.replace("k", "")) * 1000)
        elif "tr" in amt_text:
            data["amount"] = int(float(amt_text.replace("tr", "")) * 1000000)
        else:
            try:
                data["amount"] = int(amt_text)
            except:
                data["amount"] = 0
    else:
        data["amount"] = 0

    return data