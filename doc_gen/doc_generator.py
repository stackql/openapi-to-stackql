#!/usr/bin/env python3

import os
import sys
import json
import yaml
import re
import math
import psycopg
from psycopg.rows import dict_row
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ConnectionOptions:
    host: str = 'localhost'
    port: int = 5444


class StackQLDocGenerator:
    def __init__(self):
        self.connection_options = ConnectionOptions()
        self.sql_code_block_start = '```sql'
        self.yaml_code_block_start = '```yaml'
        self.code_block_end = '```'
        self.md_code_anchor = "`"
    
    def execute_sql(self, query: str) -> List[Dict]:
        """Execute SQL query against StackQL server"""
        try:
            conn = psycopg.connect(
                host=self.connection_options.host, 
                port=self.connection_options.port,
                autocommit=True,
                row_factory=dict_row
            )
            
            with conn.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchall()
            
            conn.close()
            return result
        except Exception as e:
            print(f'Error executing query: {e}')
            return []
    
    def clean_description(self, description: str) -> str:
        """Clean HTML tags from description and convert to markdown"""
        if not description:
            return ''
        
        # Replace <a> tags with markdown equivalent
        description = re.sub(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"(?:[^>]*?)>(.*?)</a>', 
                           r'[\2](\1)', description, flags=re.IGNORECASE)
        
        # Remove <p> tags and replace with space
        description = re.sub(r'</?p>', ' ', description, flags=re.IGNORECASE)
        
        # Replace <br> tags with space
        description = re.sub(r'<br\s*/?>', ' ', description, flags=re.IGNORECASE)
        
        # Replace <code> and <pre> tags with markdown code blocks
        description = re.sub(r'<(code|pre)>(.*?)</\1>', r'`\2`', description, flags=re.IGNORECASE)
        
        # Convert <ul> and <li> tags into comma-separated list
        description = re.sub(r'</?ul>', '', description, flags=re.IGNORECASE)
        description = re.sub(r'<li>(.*?)</li>', r'\1, ', description, flags=re.IGNORECASE)
        
        # Remove other HTML tags
        description = re.sub(r'</?(?:name|td|tr|table)>', '', description, flags=re.IGNORECASE)
        
        # Replace multiple spaces with single space
        description = re.sub(r'\s+', ' ', description)
        
        # Escape pipe characters for markdown tables
        description = description.replace('|', '\\|')
        
        # Remove trailing commas and spaces
        description = re.sub(r',\s*$', '', description).strip()
        
        return description
    
    def replace_all_of(self, schema: Dict, visited: set = None, depth: int = 0) -> Dict:
        """Replace allOf constructs in JSON schema"""
        if visited is None:
            visited = set()
        
        if not isinstance(schema, dict) or depth > 20:
            return schema
        
        schema_id = id(schema)
        if schema_id in visited:
            return schema
        visited.add(schema_id)
        
        if 'allOf' in schema:
            merged = {}
            for item in schema['allOf']:
                resolved_item = self.replace_all_of(item, visited, depth + 1)
                merged.update(resolved_item)
                if 'properties' in resolved_item:
                    merged.setdefault('properties', {}).update(resolved_item['properties'])
                if 'required' in resolved_item:
                    merged.setdefault('required', []).extend(resolved_item['required'])
            
            # Remove allOf and merge with existing schema
            schema = {k: v for k, v in schema.items() if k != 'allOf'}
            schema.update(merged)
            if 'required' in schema:
                schema['required'] = list(set(schema['required']))
        
        # Recursively process nested properties
        if 'properties' in schema:
            for key, prop in schema['properties'].items():
                schema['properties'][key] = self.replace_all_of(prop, visited, depth + 1)
        
        if 'items' in schema:
            if isinstance(schema['items'], list):
                schema['items'] = [self.replace_all_of(item, visited, depth + 1) for item in schema['items']]
            else:
                schema['items'] = self.replace_all_of(schema['items'], visited, depth + 1)
        
        visited.remove(schema_id)
        return schema
    
    def replace_any_of_one_of(self, schema: Dict, visited: set = None, depth: int = 0) -> Dict:
        """Replace anyOf/oneOf constructs by taking the first option"""
        if visited is None:
            visited = set()
        
        if not isinstance(schema, dict) or depth > 20:
            return schema
        
        schema_id = id(schema)
        if schema_id in visited:
            return schema
        visited.add(schema_id)
        
        if 'anyOf' in schema:
            schema = self.replace_any_of_one_of(schema['anyOf'][0], visited, depth + 1)
        elif 'oneOf' in schema:
            schema = self.replace_any_of_one_of(schema['oneOf'][0], visited, depth + 1)
        
        # Recursively process nested properties
        if isinstance(schema, dict):
            if 'properties' in schema:
                for key, prop in schema['properties'].items():
                    schema['properties'][key] = self.replace_any_of_one_of(prop, visited, depth + 1)
            
            if 'items' in schema:
                if isinstance(schema['items'], list):
                    schema['items'] = [self.replace_any_of_one_of(item, visited, depth + 1) for item in schema['items']]
                else:
                    schema['items'] = self.replace_any_of_one_of(schema['items'], visited, depth + 1)
        
        visited.remove(schema_id)
        return schema
    
    def remove_read_only_properties(self, schema: Dict, visited: set = None, depth: int = 0) -> Dict:
        """Remove readOnly properties from schema"""
        if visited is None:
            visited = set()
        
        if not isinstance(schema, dict) or depth > 20:
            return schema
        
        schema_id = id(schema)
        if schema_id in visited:
            return schema
        visited.add(schema_id)
        
        if 'properties' in schema:
            properties_to_remove = []
            for key, prop in schema['properties'].items():
                if isinstance(prop, dict) and prop.get('readOnly'):
                    properties_to_remove.append(key)
                else:
                    schema['properties'][key] = self.remove_read_only_properties(prop, visited, depth + 1)
            
            for key in properties_to_remove:
                del schema['properties'][key]
        
        if 'items' in schema:
            if isinstance(schema['items'], list):
                schema['items'] = [self.remove_read_only_properties(item, visited, depth + 1) for item in schema['items']]
            else:
                schema['items'] = self.remove_read_only_properties(schema['items'], visited, depth + 1)
        
        visited.remove(schema_id)
        return schema
    
    def get_schema_manifest(self, resource_name: str, required_params: List[str], request_body_schema: Dict) -> List[Dict]:
        """Generate schema manifest for YAML output"""
        def process_properties(properties: Dict) -> List[Dict]:
            result = []
            for key, prop in properties.items():
                # Handle allOf by merging properties
                if 'allOf' in prop:
                    merged_prop = {}
                    for item in prop['allOf']:
                        merged_prop.update(item)
                        if 'properties' in item:
                            merged_prop.setdefault('properties', {}).update(item['properties'])
                        if 'required' in item:
                            merged_prop.setdefault('required', []).extend(item['required'])
                    prop = merged_prop
                
                # Skip readOnly properties
                if prop.get('readOnly'):
                    continue
                
                prop_type = prop.get('type', 'string')
                
                # Handle nested objects
                if prop_type == 'object' and 'properties' in prop:
                    result.append({
                        'name': key,
                        'props': process_properties(prop['properties'])
                    })
                elif prop_type == 'array' and 'items' in prop and prop['items'].get('type') == 'object' and 'properties' in prop['items']:
                    result.append({
                        'name': key,
                        'value': 'array',
                        'props': process_properties(prop['items']['properties'])
                    })
                else:
                    result.append({
                        'name': key,
                        'value': prop_type
                    })
            
            return result
        
        all_props = []
        
        # Add required params as simple properties
        for param in required_params:
            all_props.append({
                'name': param,
                'value': 'string'
            })
        
        # Process request body schema properties
        if request_body_schema and 'properties' in request_body_schema:
            all_props.extend(process_properties(request_body_schema['properties']))
        
        return [{
            'name': resource_name,
            'props': all_props
        }]
    
    def generate_select_example(self, provider_name: str, service_name: str, resource_name: str, 
                              vw_resource_name: Optional[str], method: Dict, fields: List[Dict], 
                              vw_fields: List[Dict]) -> str:
        """Generate SELECT SQL example"""
        ret_select_stmt = f"""
## {self.md_code_anchor}SELECT{self.md_code_anchor} examples

{self.clean_description(method.get('description', ''))}

"""
        
        # Check if there is a view resource, use tabs if so
        if vw_fields:
            ret_select_stmt += "<Tabs " + \
                '    defaultValue="view"' + \
                '    values={[' + \
                '           { label: ' + f"'{vw_resource_name}', value: 'view'" + '},' + \
                '           { label: ' + f"'{resource_name}', value: 'resource'" + '},' + \
                '    ]}' + \
                '>' + \
                '<TabItem value="view">\n\n'

            # View select columns
            vw_select_columns = ',\n'.join([field['name'] for field in vw_fields])
            
            # Where clause for view
            vw_where_clause = ''
            if method.get('RequiredParams'):
                params = [param.strip() for param in method['RequiredParams'].split(',')]
                vw_where_clause = "WHERE " + " AND ".join([param + " = '{{ " + param + " }}'" for param in params])
            
            ret_select_stmt += f"""
{self.sql_code_block_start}
SELECT
{vw_select_columns}
FROM {provider_name}.{service_name}.{vw_resource_name}
{vw_where_clause};
{self.code_block_end}
</TabItem>
<TabItem value="resource">

"""
        
        # Resource SQL
        select_columns = ',\n'.join([field['name'] for field in fields])
        
        # Where clause for resource
        where_clause = ''
        if method.get('RequiredParams'):
            params = [param.strip() for param in method['RequiredParams'].split(',')]
            where_clause = "WHERE " + " AND ".join([param + " = '{{ " + param + " }}'" for param in params])
        
        ret_select_stmt += f"""
{self.sql_code_block_start}
SELECT
{select_columns}
FROM {provider_name}.{service_name}.{resource_name}
{where_clause};
{self.code_block_end}"""
        
        if vw_fields:
            ret_select_stmt += """
</TabItem></Tabs>

"""
        
        return ret_select_stmt
    
    def generate_insert_example(self, provider_name: str, service_name: str, resource_name: str,
                               resource_data: Dict, dereferenced_api: Dict, method: Dict) -> str:
        """Generate INSERT SQL example"""
        try:
            print(f"Processing insert for {resource_name}...")
            
            required_params = []
            if method.get('RequiredParams'):
                required_params = [param.strip() for param in method['RequiredParams'].split(',')]
            
            # Get operation reference and extract request body schema
            request_body_schema = None
            if 'methods' in resource_data and method['MethodName'] in resource_data['methods']:
                operation_ref = resource_data['methods'][method['MethodName']]['operation'].get('$ref', '')
                if operation_ref:
                    # Parse operation path and verb
                    operation_parts = operation_ref.replace('#/paths/', '').replace('~1', '/').split('/')
                    operation_verb = operation_parts[-1]
                    operation_path = '/'.join(operation_parts[:-1])
                    
                    # Access dereferenced API
                    path_obj = dereferenced_api.get('paths', {}).get(operation_path)
                    if path_obj and operation_verb in path_obj:
                        operation_obj = path_obj[operation_verb]
                        if 'requestBody' in operation_obj:
                            content = operation_obj['requestBody'].get('content', {})
                            app_json = content.get('application/json', {})
                            request_body_schema = app_json.get('schema', {})
                            
                            # Process schema
                            request_body_schema = self.replace_all_of(request_body_schema)
                            request_body_schema = self.replace_any_of_one_of(request_body_schema)
                            request_body_schema = self.remove_read_only_properties(request_body_schema)
            
            # Remove "data__" prefix from required params if it exists
            normalized_required_params = [
                field[6:] if field.startswith("data__") else field 
                for field in required_params
            ]
            
            # INSERT column lists
            req_body_required_fields_col_list = []
            req_body_all_fields_col_list = []
            
            if request_body_schema:
                req_body_required_fields_col_list = [
                    f"data__{field}" for field in request_body_schema.get('required', [])
                ]
                req_body_all_fields_col_list = [
                    f"data__{field}" for field in request_body_schema.get('properties', {}).keys()
                ]
            
            required_insert_fields = list(set(req_body_required_fields_col_list + required_params))
            all_insert_fields = list(set(req_body_all_fields_col_list + required_params))
            
            # INSERT select values
            req_body_required_fields_select_vals = [
                f"'{{ {field} }}'" for field in request_body_schema.get('required', [])
            ] if request_body_schema else []
            
            req_body_all_fields_select_vals = [
                f"'{{ {field} }}'" for field in request_body_schema.get('properties', {}).keys()
            ] if request_body_schema else []
            
            required_select_values = list(set(
                req_body_required_fields_select_vals + 
                [f"'{{ {field} }}'" for field in normalized_required_params]
            ))
            all_select_values = list(set(
                req_body_all_fields_select_vals + 
                [f"'{{ {field} }}'" for field in normalized_required_params]
            ))
            
            # Check if 'Required Properties' tab should be added
            should_add_required_tab = (
                len(required_insert_fields) > 0 and 
                len(required_insert_fields) != len(all_insert_fields)
            )
            
            # Generate YAML manifest
            yaml_manifest = yaml.dump(
                self.get_schema_manifest(resource_name, required_params, request_body_schema),
                default_flow_style=False,
                allow_unicode=True
            )
            
            # Create insert example with tabs
            insert_example = f"""
## {self.md_code_anchor}INSERT{self.md_code_anchor} example

Use the following StackQL query and manifest file to create a new <code>{resource_name}</code> resource.

"""
            
            tabs_values = []
            if should_add_required_tab:
                tabs_values.append("{ label: 'Required Properties', value: 'required' }")
            tabs_values.append("{ label: 'All Properties', value: 'all' }")
            tabs_values.append("{ label: 'Manifest', value: 'manifest' }")
            
            tabs_config_str = ", ".join(tabs_values)
            
            insert_example += "<Tabs " + \
                '    defaultValue="all"' + \
                '    values={[' + \
                f'        {tabs_config_str}' + \
                '    ]}' + \
                '>'
            
            # All properties tab
            all_fields_str = ",\n".join(all_insert_fields)
            all_values_str = ",\n".join(all_select_values)
            
            insert_example += f"""
<TabItem value="all">

{self.sql_code_block_start}
/*+ create */
INSERT INTO {provider_name}.{service_name}.{resource_name} (
{all_fields_str}
)
SELECT 
{all_values_str}
;
{self.code_block_end}
</TabItem>"""
            
            # Required properties tab (if needed)
            if should_add_required_tab:
                required_fields_str = ",\n".join(required_insert_fields)
                required_values_str = ",\n".join(required_select_values)
                insert_example += f"""
<TabItem value="required">

{self.sql_code_block_start}
/*+ create */
INSERT INTO {provider_name}.{service_name}.{resource_name} (
{required_fields_str}
)
SELECT 
{required_values_str}
;
{self.code_block_end}
</TabItem>"""
            
            # Manifest tab
            insert_example += f"""
<TabItem value="manifest">

{self.yaml_code_block_start}
{yaml_manifest}
{self.code_block_end}
</TabItem>
</Tabs>
"""
            
            return insert_example
        except Exception as e:
            print(f'Error generating INSERT example: {e}')
            return ''
    
    def generate_update_example(self, provider_name: str, service_name: str, resource_name: str,
                               resource_data: Dict, dereferenced_api: Dict, method: Dict, 
                               is_replace: bool = False) -> str:
        """Generate UPDATE/REPLACE SQL example"""
        try:
            print(f"Processing update for {resource_name}...")
            
            required_params = []
            if method.get('RequiredParams'):
                required_params = [param.strip() for param in method['RequiredParams'].split(',')]
            
            # Get operation reference and extract request body schema
            request_body_schema = None
            if 'methods' in resource_data and method['MethodName'] in resource_data['methods']:
                operation_ref = resource_data['methods'][method['MethodName']]['operation'].get('$ref', '')
                if operation_ref:
                    # Parse operation path and verb
                    operation_parts = operation_ref.replace('#/paths/', '').replace('~1', '/').split('/')
                    operation_verb = operation_parts[-1]
                    operation_path = '/'.join(operation_parts[:-1])
                    
                    # Access dereferenced API
                    path_obj = dereferenced_api.get('paths', {}).get(operation_path)
                    if path_obj and operation_verb in path_obj:
                        operation_obj = path_obj[operation_verb]
                        if 'requestBody' in operation_obj:
                            content = operation_obj['requestBody'].get('content', {})
                            app_json = content.get('application/json', {})
                            request_body_schema = app_json.get('schema', {})
                            
                            # Process schema
                            request_body_schema = self.replace_all_of(request_body_schema)
                            request_body_schema = self.replace_any_of_one_of(request_body_schema)
                            request_body_schema = self.remove_read_only_properties(request_body_schema)
            
            # Generate SET clause
            set_params = []
            if request_body_schema and 'properties' in request_body_schema:
                for field, field_schema in request_body_schema['properties'].items():
                    field_type = field_schema.get('type', 'string')
                    if field_type == 'string':
                        set_params.append(f"{field} = '{{ {field} }}'")
                    elif field_type == 'boolean':
                        set_params.append(f"{field} = true|false")
                    elif field_type == 'number':
                        set_params.append(f"{field} = number")
                    else:
                        set_params.append(f"{field} = '{{ {field} }}'")
            
            # Generate WHERE clause
            where_clauses = [f"{param} = '{{ {param} }}'" for param in required_params]
            where_clause = ' AND '.join(where_clauses)
            
            # Description based on operation type
            operation_type = 'REPLACE' if is_replace else 'UPDATE'
            if is_replace:
                sql_description = f"Replaces all fields in the specified <code>{resource_name}</code> resource."
            else:
                sql_description = f"Updates a <code>{resource_name}</code> resource."
            
            return f"""
## {self.md_code_anchor}{operation_type}{self.md_code_anchor} example

{sql_description}

{self.sql_code_block_start}
/*+ update */
{operation_type} {provider_name}.{service_name}.{resource_name}
SET 
{','.join(set_params)}
WHERE 
{where_clause};
{self.code_block_end}
"""
        except Exception as e:
            print(f'Error generating UPDATE example: {e}')
            return ''
    
    def generate_delete_example(self, provider_name: str, service_name: str, resource_name: str,
                               method: Dict) -> str:
        """Generate DELETE SQL example"""
        required_params = []
        if method.get('RequiredParams'):
            required_params = [param.strip() for param in method['RequiredParams'].split(',')]
        
        where_clauses = [f"{param} = '{{ {param} }}'" for param in required_params]
        where_clause = ' AND '.join(where_clauses)
        
        return f"""
## {self.md_code_anchor}DELETE{self.md_code_anchor} example

Deletes the specified <code>{resource_name}</code> resource.

{self.sql_code_block_start}
/*+ delete */
DELETE FROM {provider_name}.{service_name}.{resource_name}
WHERE {where_clause};
{self.code_block_end}
"""
    
    def create_resource_index_content(self, provider_name: str, service_name: str, 
                                    resource_name: str, vw_resource_name: Optional[str],
                                    resource_data: Dict, paths: Dict, 
                                    components_schemas: Dict, 
                                    components_request_bodies: Dict,
                                    dereferenced_api: Dict) -> str:
        """Create resource index content"""
        
        # Fetch field descriptions
        fields_sql = f"DESCRIBE EXTENDED {provider_name}.{service_name}.{resource_name}"
        fields = self.execute_sql(fields_sql)
        
        vw_fields = []
        merged_fields = []
        
        if vw_resource_name:
            vw_fields_sql = f"DESCRIBE EXTENDED {provider_name}.{service_name}.{vw_resource_name}"
            vw_fields = self.execute_sql(vw_fields_sql)
            
            # Merge fields into vw_fields with fallback for missing descriptions
            fields_map = {field['name']: field for field in fields}
            
            merged_fields = []
            for vw_field in vw_fields:
                matching_field = fields_map.get(vw_field['name'], {})
                merged_field = {
                    **vw_field,
                    'type': vw_field.get('type') or matching_field.get('type') or 'text',
                    'description': (
                        vw_field.get('description') or 
                        matching_field.get('description') or 
                        'field from the parent object'
                    )
                }
                merged_fields.append(merged_field)
        
        # Fetch method descriptions
        methods_sql = f"SHOW EXTENDED METHODS IN {provider_name}.{service_name}.{resource_name}"
        methods = self.execute_sql(methods_sql)
        
        # Start building the markdown content
        content = f"""---
title: {resource_name}
hide_title: false
hide_table_of_contents: false
keywords:
  - {resource_name}
  - {service_name}
  - {provider_name}
  - infrastructure-as-code
  - configuration-as-data
  - cloud inventory
description: Query, deploy and manage {provider_name} resources using SQL
custom_edit_url: null
image: /img/providers/{provider_name}/stackql-{provider_name}-provider-featured-image.png
---

import CopyableCode from '@site/src/components/CopyableCode/CopyableCode';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

Creates, updates, deletes, gets or lists a <code>{resource_name}</code> resource.

## Overview
<table><tbody>
<tr><td><b>Name</b></td><td><code>{resource_name}</code></td></tr>
<tr><td><b>Type</b></td><td>Resource</td></tr>
<tr><td><b>Id</b></td><td><CopyableCode code="{resource_data.get('id', '')}" /></td></tr>
</tbody></table>

## Fields
"""
        
        if not fields:
            # No fields
            content += f"{self.md_code_anchor}SELECT{self.md_code_anchor} not supported for this resource, use {self.md_code_anchor}SHOW METHODS{self.md_code_anchor} to view available operations for the resource.\n\n"
        else:
            if merged_fields:
                # We have a view, use tabs
                content += "<Tabs " + \
                    '    defaultValue="view"' + \
                    '    values={[' + \
                    '       { label: ' + f"'{vw_resource_name}'" + ', value: "view" },' + \
                    '       { label: ' + f"'{resource_name}'" + ', value: "resource" },' + \
                    '    ]}' + \
                    '>' + \
                    '<TabItem value="view">\n'

                content += '| Name | Datatype | Description |\n|:-----|:---------|:------------|\n'
                for field in merged_fields:
                    content += f"| <CopyableCode code=\"{field['name']}\" /> | {self.md_code_anchor}{field['type']}{self.md_code_anchor} | {self.clean_description(field['description'])} |\n"
                content += '</TabItem>\n'
                content += '<TabItem value="resource">\n'
                content += '\n'
            
            # Normal fields
            content += '| Name | Datatype | Description |\n|:-----|:---------|:------------|\n'
            for field in fields:
                content += f"| <CopyableCode code=\"{field['name']}\" /> | {self.md_code_anchor}{field['type']}{self.md_code_anchor} | {self.clean_description(field['description'])} |\n"
            
            # Close tabs
            if vw_fields:
                content += '</TabItem></Tabs>\n'
        
        content += '\n## Methods\n| Name | Accessible by | Required Params | Description |\n|:-----|:--------------|:----------------|:------------|\n'
        
        # Append methods
        for method in methods:
            sql_verb = method['SQLVerb']
            content += f"| <CopyableCode code=\"{method['MethodName']}\" /> | {self.md_code_anchor}{sql_verb}{self.md_code_anchor} | <CopyableCode code=\"{method['RequiredParams']}\" /> | {self.clean_description(method['description'])} |\n"
        
        # Append SQL examples for each SQL verb
        sql_verbs = ['SELECT', 'INSERT', 'UPDATE', 'REPLACE', 'DELETE']
        for sql_verb in sql_verbs:
            relevant_methods = [method for method in methods if method['SQLVerb'] == sql_verb]
            
            if not relevant_methods:
                continue
            
            # Sort by required params length and take the first one
            example_method = sorted(relevant_methods, key=lambda m: len(m.get('RequiredParams', '')))[0]
            
            if sql_verb == 'SELECT':
                content += self.generate_select_example(
                    provider_name, service_name, resource_name, vw_resource_name,
                    example_method, fields, vw_fields
                )
            elif sql_verb == 'INSERT':
                content += self.generate_insert_example(
                    provider_name, service_name, resource_name, resource_data,
                    dereferenced_api, example_method
                )
            elif sql_verb == 'UPDATE':
                content += self.generate_update_example(
                    provider_name, service_name, resource_name, resource_data,
                    dereferenced_api, example_method
                )
            elif sql_verb == 'REPLACE':
                content += self.generate_update_example(
                    provider_name, service_name, resource_name, resource_data,
                    dereferenced_api, example_method, is_replace=True
                )
            elif sql_verb == 'DELETE':
                content += self.generate_delete_example(
                    provider_name, service_name, resource_name, example_method
                )
        
        return content
    
    def process_resource(self, provider_name: str, service_folder: str, service_name: str, resource: Dict):
        """Process a single resource"""
        print(f"Processing resource: {resource['name']}")
        
        resource_folder = os.path.join(service_folder, resource['name'])
        os.makedirs(resource_folder, exist_ok=True)
        
        resource_index_path = os.path.join(resource_folder, 'index.md')
        resource_index_content = self.create_resource_index_content(
            provider_name, 
            service_name, 
            resource['name'], 
            resource['vwResourceName'], 
            resource['resourceData'], 
            resource['paths'], 
            resource['componentsSchemas'], 
            resource['componentsRequestBodies'],
            resource['dereferencedAPI']
        )
        
        with open(resource_index_path, 'w', encoding='utf-8') as f:
            f.write(resource_index_content)
    
    def generate_resource_links(self, provider_name: str, service_name: str, resources: List[Dict]) -> str:
        """Generate resource links for the service index"""
        resource_links = []
        for resource in resources:
            resource_links.append(f'<a href="/providers/{provider_name}/{service_name}/{resource["name"]}/">{resource["name"]}</a>')
        return '<br />\n'.join(resource_links)
    
    def create_service_index_content(self, provider_name: str, service_name: str, resources: List[Dict]) -> str:
        """Create service index content"""
        total_resources = len(resources)
        
        # Sort resources alphabetically by name
        resources.sort(key=lambda x: x['name'])
        
        half_length = math.ceil(total_resources / 2)
        first_column_resources = resources[:half_length]
        second_column_resources = resources[half_length:]
        
        # Generate the HTML for resource links
        first_column_links = self.generate_resource_links(provider_name, service_name, first_column_resources)
        second_column_links = self.generate_resource_links(provider_name, service_name, second_column_resources)
        
        return f"""---
title: {service_name}
hide_title: false
hide_table_of_contents: false
keywords:
  - {service_name}
  - {provider_name}
  - stackql
  - infrastructure-as-code
  - configuration-as-data
  - cloud inventory
description: Query, deploy and manage {provider_name} resources using SQL
custom_edit_url: null
image: /img/providers/{provider_name}/stackql-{provider_name}-provider-featured-image.png
---

{service_name} service documentation.

:::info Service Summary

<div class="row">
<div class="providerDocColumn">
<span>total resources:&nbsp;<b>{total_resources}</b></span><br />
</div>
</div>

:::

## Resources
<div class="row">
<div class="providerDocColumn">
{first_column_links}
</div>
<div class="providerDocColumn">
{second_column_links}
</div>
</div>"""
    
    def create_docs_for_service(self, yaml_file_path: str, provider_name: str, service_name: str, service_folder: str, dereferenced_api: Dict):
        """Process each service sequentially"""
        with open(yaml_file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Create service directory
        os.makedirs(service_folder, exist_ok=True)
        
        resources_obj = data.get('components', {}).get('x-stackQL-resources', {})
        components_schemas = data.get('components', {}).get('schemas', {})
        components_request_bodies = data.get('components', {}).get('requestBodies', {})
        paths = data.get('paths', {})
        
        if not resources_obj:
            print(f"No resources found in {yaml_file_path}")
            return
        
        resources = []
        for resource_name, resource_data in resources_obj.items():
            # Skip resources that start with "vw_"
            if resource_name.startswith('vw_'):
                continue
            
            if not resource_data.get('id'):
                print(f"No 'id' defined for resource: {resource_name} in service: {service_name}")
                continue
            
            # Check if there's a corresponding "vw_" resource
            vw_resource_name = f"vw_{resource_name}"
            has_vw_resource = vw_resource_name in resources_obj
            
            resources.append({
                'name': resource_name,
                'vwResourceName': vw_resource_name if has_vw_resource else None,
                'resourceData': resource_data,
                'paths': paths,
                'componentsSchemas': components_schemas,
                'componentsRequestBodies': components_request_bodies,
                'dereferencedAPI': dereferenced_api
            })
        
        # Process service index
        service_index_path = os.path.join(service_folder, 'index.md')
        service_index_content = self.create_service_index_content(provider_name, service_name, resources)
        with open(service_index_path, 'w', encoding='utf-8') as f:
            f.write(service_index_content)
        
        # Process each resource
        for resource in resources:
            self.process_resource(provider_name, service_folder, service_name, resource)
        
        print(f"Generated documentation for {service_name}")
    
    def services_to_markdown(self, provider_name: str, services_list: List[str]) -> str:
        """Convert services to markdown links"""
        return '\n'.join([f'<a href="/providers/{provider_name}/{service}/">{service}</a><br />' for service in services_list])
    
    def doc(self, provider_name: str):
        """Main doc function"""
        project_root = os.getcwd()
        dir_name = os.path.basename(project_root)
        
        if dir_name != 'openapi-to-stackql':
            print("Must be run from openapi-to-stackql project root...")
            raise Exception('Must be run from openapi-to-stackql project root')
        
        print(f"Documenting {provider_name}...")
        
        provider_dir = f"providers/src/{provider_name}/v00.00.00000"
        docs_dir = f"provider_docs/{provider_name}-docs"
        
        # Clean up existing docs
        index_path = os.path.join(docs_dir, 'index.md')
        if os.path.exists(index_path):
            os.remove(index_path)
        
        providers_path = os.path.join(docs_dir, 'providers')
        if os.path.exists(providers_path):
            import shutil
            shutil.rmtree(providers_path)
        
        # Initialize provider index
        services_for_index = []
        
        # Check for header content files
        header_content1_path = f"doc_gen/provider_data/{provider_name}/headerContent1.txt"
        header_content2_path = f"doc_gen/provider_data/{provider_name}/headerContent2.txt"
        
        if not os.path.exists(header_content1_path) or not os.path.exists(header_content2_path):
            print(f"Missing headerContent1.txt or headerContent2.txt for {provider_name}...")
            raise Exception(f"Missing headerContent1.txt or headerContent2.txt for {provider_name}")
        
        # Static header content
        with open(header_content1_path, 'r', encoding='utf-8') as f:
            header_content1 = f.read()
        with open(header_content2_path, 'r', encoding='utf-8') as f:
            header_content2 = f.read()
        
        # Initialize counters
        total_services_count = 0
        
        # Process each YAML file one by one
        service_dir = os.path.join(provider_dir, 'services')
        print(f"Processing services in {service_dir}...")
        
        # For simplicity, we'll create a mock dereferenced API
        # In a real implementation, you'd use a proper OpenAPI dereferencer
        dereferenced_api = {'paths': {}}
        
        if os.path.exists(service_dir):
            service_files = [f for f in os.listdir(service_dir) if f.endswith('.yaml')]
            
            for file in service_files:
                service_name = os.path.splitext(file)[0].replace('-', '_')
                print(f"Processing service : {service_name}")
                services_for_index.append(service_name)
                file_path = os.path.join(service_dir, file)
                total_services_count += 1
                service_folder = os.path.join(docs_dir, 'providers', provider_name, service_name)
                self.create_docs_for_service(file_path, provider_name, service_name, service_folder, dereferenced_api)
        
        print(f"Processed {total_services_count} services")
        
        # Calculate total resources count
        total_resources_count = 0
        provider_services_path = os.path.join(docs_dir, 'providers', provider_name)
        if os.path.exists(provider_services_path):
            for service_dir_name in os.listdir(provider_services_path):
                service_path = os.path.join(provider_services_path, service_dir_name)
                if os.path.isdir(service_path):
                    resource_count = len([d for d in os.listdir(service_path) if os.path.isdir(os.path.join(service_path, d))])
                    total_resources_count += resource_count
        
        print(f"Processed {total_resources_count} resources")
        
        # Make sure services_for_index is unique
        services_for_index = list(set(services_for_index))
        services_for_index.sort()
        
        # Split services into two columns
        half = math.ceil(len(services_for_index) / 2)
        first_column_services = services_for_index[:half]
        second_column_services = services_for_index[half:]
        
        # Create the content for the index file
        index_content = f"""{header_content1}

:::info Provider Summary

<div class="row">
<div class="providerDocColumn">
<span>total services:&nbsp;<b>{total_services_count}</b></span><br />
<span>total resources:&nbsp;<b>{total_resources_count}</b></span><br />
</div>
</div>

:::

{header_content2}

## Services
<div class="row">
<div class="providerDocColumn">
{self.services_to_markdown(provider_name, first_column_services)}
</div>
<div class="providerDocColumn">
{self.services_to_markdown(provider_name, second_column_services)}
</div>
</div>
"""
        
        # Write the index file
        os.makedirs(docs_dir, exist_ok=True)
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"Index file created at {index_path}")
        
        # Copy MDX file
        mdx_source = f"doc_gen/provider_data/{provider_name}/stackql-provider-registry.mdx"
        mdx_dest = os.path.join(docs_dir, 'stackql-provider-registry.mdx')
        if os.path.exists(mdx_source):
            import shutil
            shutil.copy2(mdx_source, mdx_dest)
            print("MDX file copied")
    
    def generate_docs(self, provider_name: str):
        """Generate docs with error handling"""
        try:
            self.doc(provider_name)
            print("Finished documenting!")
        except Exception as err:
            print(f"Error: {err}")
            raise err


# Main entry point
def main():
    if len(sys.argv) < 2:
        print("Usage: python doc_generator.py <provider_name>")
        sys.exit(1)
    
    provider_name = sys.argv[1]
    generator = StackQLDocGenerator()
    generator.generate_docs(provider_name)


if __name__ == "__main__":
    main()