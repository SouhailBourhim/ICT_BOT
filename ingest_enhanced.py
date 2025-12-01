#!/usr/bin/env python3
"""
Enhanced document ingestion script with semantic chunking and metadata extraction.
"""
import sys
import os
import argparse
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processors.ingestion_pipeline import IngestionPipeline


def main():
    parser = argparse.ArgumentParser(description="Enhanced document ingestion pipeline")
    parser.add_argument("--data-path", default="data", help="Path to data directory")
    parser.add_argument("--chroma-path", default="chroma", help="Path to ChromaDB directory")
    parser.add_argument("--metadata-db", default="metadata.db", help="Path to metadata database")
    parser.add_argument("--embedding-model", default="llama3", help="Embedding model to use")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before ingestion")
    parser.add_argument("--files", nargs="+", help="Specific files to process")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    
    args = parser.parse_args()
    
    # Initialize pipeline
    try:
        pipeline = IngestionPipeline(
            data_path=args.data_path,
            chroma_path=args.chroma_path,
            metadata_db_path=args.metadata_db,
            embedding_model=args.embedding_model
        )
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {e}")
        sys.exit(1)
    
    # Check if data directory exists
    if not Path(args.data_path).exists():
        Path(args.data_path).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created data directory: {args.data_path}")
        print("Please add your documents to this directory and run the script again.")
        return
    
    # Run ingestion
    try:
        results = pipeline.ingest_documents(
            file_paths=args.files,
            show_progress=not args.quiet,
            clear_existing=args.clear
        )
        
        # Print results
        print("\n🎉 Ingestion completed!")
        print(f"📊 Files processed: {results['files_processed']}")
        print(f"🧩 Chunks created: {results['chunks_created']}")
        print(f"⏱️  Duration: {results['duration']:.2f} seconds")
        
        if results['errors']:
            print(f"⚠️  Errors: {len(results['errors'])}")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(results['errors']) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")
        
    except KeyboardInterrupt:
        print("\n⏹️  Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()