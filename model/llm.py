from pypdf import PdfReader
from transformers import AutoModelForCausalLM, AutoTokenizer

def read_doc(pdf_path):
    reader = PdfReader(pdf_path)
    all_text = ""
    for page in reader.pages:
        all_text += page.extract_text()
    return all_text

def init_model(model_name):
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto"
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    return model, tokenizer

keyword_system_prompt = """
Identify the only five key technical keywords (Do not list five keywords).

Output format (strictly follow this format):
Keywords: [keyword 1,2,3,4,5]
"""

abstract_system_prompt = """
Provide a summary of the paper in three concise statements, highlighting:
 - Main objectives
 - Key methods or approaches
 - Primary findings

Output format (strictly follow this format):
Summary:
1. [Main objective]
2. [Key methods or approaches]
3. [Primary findings]
"""

# 2. Extract the GitHub repository link if provided by the authors.
repo_system_prompt = """
Extract the paper's Github or Gitlab repository link. If not provided, state 'I don't know'
"""

def ask(model, tokenizer, system_prompt, user_prompt, max_token):
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=max_token
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return response

def collect_paper_info(model_path, paper_path):
    model, tokenizer = init_model(model_path)
    user_prompt = read_doc(paper_path)
    response1 = ask(model, tokenizer, keyword_system_prompt, user_prompt, 32)
    response2 = ask(model, tokenizer, abstract_system_prompt, user_prompt, 128)
    response3 = ask(model, tokenizer, repo_system_prompt, user_prompt, 64)
    return [response1, response2, response3]

def main():
    [keywords, abstract, repo] = collect_paper_info("Qwen/Qwen2.5-1.5B-Instruct", "fuzz4all.pdf")
    print("------------------------------------------------------------")
    print(keywords)
    print("------------------------------------------------------------")
    print(abstract)
    print("------------------------------------------------------------")
    print(repo)

if __name__ == "__main__":
    main()
