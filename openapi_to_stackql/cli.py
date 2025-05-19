import argparse
import sys
from openapi_to_stackql import analyze

def main():
    parser = argparse.ArgumentParser(description="StackQL Provider Generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze OpenAPI specs and generate CSV summaries")
    analyze_parser.add_argument("--input", required=True, help="Input directory with OpenAPI specs")
    analyze_parser.add_argument("--output", required=True, help="Output directory for CSV files")

    args = parser.parse_args()

    # Route to subcommand
    if args.command == "analyze":
        analyze.run(input_dir=args.input, output_dir=args.output)
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
