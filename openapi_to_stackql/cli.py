import argparse
import sys
from openapi_to_stackql import analyze, convert

def main():
    parser = argparse.ArgumentParser(description="StackQL Provider Generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze OpenAPI specs and generate CSV summaries")
    analyze_parser.add_argument("--input", required=True, help="Input directory with OpenAPI specs")
    analyze_parser.add_argument("--output", required=True, help="Output directory for CSV files")

    convert_parser = subparsers.add_parser("convert", help="Convert OpenAPI specs to StackQL provider specs")
    convert_parser.add_argument("--input", required=True, help="Input directory with OpenAPI specs")
    convert_parser.add_argument("--output", required=True, help="Output directory for StackQL specs")
    convert_parser.add_argument("--config", required=True, help="Path to the enriched CSV manifest")
    convert_parser.add_argument("--provider", required=True, help="Provider name for the stackql provider")
    convert_parser.add_argument(
    "--servers",
    required=False,
    help="Optional JSON string to override the 'servers' block in the output specs"
    )
    convert_parser.add_argument(
    "--provider-config",
    required=False,
    help="Optional JSON string used for provider configuration"
    )
    convert_parser.add_argument(
        "--skip",
        required=False,
        help="Comma-separated list of filenames to skip (e.g., foo.yaml,bar.yaml)"
    )

    args = parser.parse_args()

    # Route to subcommand
    if args.command == "analyze":
        analyze.run(input_dir=args.input, output_dir=args.output)
    elif args.command == "convert":
        convert.run(input_dir=args.input, output_dir=args.output, config_path=args.config, provider_id=args.provider, servers=args.servers, provider_config=args.provider_config ,skip_files=args.skip)
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
