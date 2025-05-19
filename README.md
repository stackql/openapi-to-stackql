bash ./bin/openapi-to-stackql.sh \
  --input examples/aws/services \
  --output output/aws \
  --config examples/aws/config.yaml

bash ./bin/openapi-to-stackql.sh analyze \
--input source/snowflake --output output/snowflake
