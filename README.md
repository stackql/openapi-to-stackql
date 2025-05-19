bash ./bin/openapi-to-stackql.sh \
  --input examples/aws/services \
  --output output/aws \
  --config examples/aws/config.yaml

bash ./bin/openapi-to-stackql.sh analyze \
--input source/snowflake --output output/snowflake

bash ./bin/openapi-to-stackql.sh convert \
--input source/snowflake --output providers/snowflake --config config/snowflake/snowflake.csv --provider snowflake \
--servers '[{"url":"https://{organization}.snowflakecomputing.com/","variables":{"organization":{"default":"org-account"}}}]' \
--skip common.yaml
