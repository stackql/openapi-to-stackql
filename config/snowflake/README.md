bash ./config/snowflake/pre_process.sh source/snowflake

bash ./bin/openapi-to-stackql.sh convert \
--input source/snowflake --output providers/snowflake --config config/snowflake/snowflake.csv --provider snowflake \
--servers '[{"url":"https://{organization}.snowflakecomputing.com/","variables":{"organization":{"default":"org-account"}}}]' \
--skip common.yaml