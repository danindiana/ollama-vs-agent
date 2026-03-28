import argparse
import asyncio
import hashlib
import os
import sqlite3
import datetime
from pathlib import Path
import httpx

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is not installed. Please run: pip install -r requirements.txt")
    exit(1)

OLLAMA_API_URL = "http://localhost:11434/api/generate"

def init_db(db_path):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                model_used TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                output_hash TEXT NOT NULL,
                UNIQUE(filename, model_used)
            )
        """)
        conn.commit()

def is_already_processed(db_path, filename, model_used):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM processed_papers WHERE filename = ? AND model_used = ?",
            (filename, model_used)
        )
        return cursor.fetchone() is not None

def log_processed_paper(db_path, filename, model_used, output_content):
    output_hash = hashlib.sha256(output_content.encode('utf-8')).hexdigest()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO processed_papers (filename, model_used, output_hash)
            VALUES (?, ?, ?)
        """, (filename, model_used, output_hash))
        conn.commit()

def extract_text_from_pdf(pdf_path, max_pages=5):
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(min(max_pages, len(doc))):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text

async def summarize_and_refactor(text, model, num_ctx):
    prompt = (
        "Analyze the attached text from an AI/ML paper. 1. Summarize the core contribution. "
        "2. Refactor the implementation or logical core into: (a) Symbolic Logic, "
        "(b) Lambda Calculus, (c) Haskell types/functions, and (d) C++ template-style meta-logic.\n\n"
        f"TEXT:\n{text[:8000]}"
    )
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(OLLAMA_API_URL, json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": num_ctx
            }
        })
        response.raise_for_status()
        result = response.json()
        return result.get("response", "")

async def process_pdf(pdf_path, db_path, output_dir, model, num_ctx, verbose=False):
    filename = os.path.basename(pdf_path)
    if is_already_processed(db_path, filename, model):
        if verbose:
            print(f"Skipping {filename}: Already processed with model {model}.")
        return

    print(f"Processing: {filename}...")
    try:
        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            print(f"Warning: Extracted text from {filename} is empty.")
            return

        result_content = await summarize_and_refactor(text, model, num_ctx)
        
        if result_content:
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"PROCESSED_{filename}.md")
            
            # Format the output with model provenance metadata
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            provenance_header = (
                f"---\n"
                f"source_file: {filename}\n"
                f"processed_at: {now}\n"
                f"model: {model}\n"
                f"num_ctx: {num_ctx}\n"
                f"---\n\n"
            )
            final_content = provenance_header + result_content
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(final_content)
                
            log_processed_paper(db_path, filename, model, final_content)
            if verbose:
                print(f"Completed {filename}. Output saved to {output_file}.")
        else:
            print(f"Error: Model returned empty response for {filename}.")
            
    except Exception as e:
        print(f"Failed processing {filename}: {e}")

async def main_async(args):
    init_db(args.db_path)
    
    pdfs = []
    target_path = Path(args.path)
    if target_path.is_file() and target_path.suffix.lower() == '.pdf':
        pdfs.append(str(target_path))
    elif target_path.is_dir():
        pdfs = [str(p) for p in target_path.glob("*.pdf")]
        
    if not pdfs:
        print("No PDFs found to process.")
        return
        
    if args.verbose:
        print(f"Found {len(pdfs)} PDF(s) to process. Model: {args.model}")

    tasks = []
    # If dealing with large models and limited VRAM, concurrency might need to be 1.
    # But asyncio wrapper is there for I/O overlap and readiness.
    # Currently Ollama processes sequentially if OLLAMA_NUM_PARALLEL=1 anyway.
    for pdf_path in pdfs:
        await process_pdf(pdf_path, args.db_path, args.output_dir, args.model, args.num_ctx, args.verbose)

def main():
    parser = argparse.ArgumentParser(description="Research Pipeline - AI Paper Refactor")
    parser.add_argument("path", help="PDF file or directory containing PDFs")
    parser.add_argument("--db", dest="db_path", default="pipeline_state.db", help="Path to SQLite ledger")
    parser.add_argument("--out", dest="output_dir", default="research_outputs", help="Output directory for processed MD files")
    parser.add_argument("--model", default="deepseek-r1:32b", help="Ollama model to use")
    parser.add_argument("--ctx", dest="num_ctx", type=int, default=16384, help="Context window size (num_ctx)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    asyncio.run(main_async(args))

if __name__ == "__main__":
    main()
