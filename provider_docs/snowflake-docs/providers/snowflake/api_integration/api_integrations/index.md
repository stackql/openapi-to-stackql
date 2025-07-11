---
title: api_integrations
hide_title: false
hide_table_of_contents: false
keywords:
  - api_integrations
  - api_integration
  - snowflake
  - infrastructure-as-code
  - configuration-as-data
  - cloud inventory
description: Query, deploy and manage snowflake resources using SQL
custom_edit_url: null
image: /img/providers/snowflake/stackql-snowflake-provider-featured-image.png
---

import CopyableCode from '@site/src/components/CopyableCode/CopyableCode';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

Creates, updates, deletes, gets or lists a <code>api_integrations</code> resource.

## Overview
<table><tbody>
<tr><td><b>Name</b></td><td><code>api_integrations</code></td></tr>
<tr><td><b>Type</b></td><td>Resource</td></tr>
<tr><td><b>Id</b></td><td><CopyableCode code="snowflake.api_integration.api_integrations" /></td></tr>
</tbody></table>

## Fields
| Name | Datatype | Description |
|:-----|:---------|:------------|
| <CopyableCode code="name" /> | `string` | Name of the API integration. |
| <CopyableCode code="api_allowed_prefixes" /> | `array` | A comma-separated list of endpoints and resources that Snowflake can access. |
| <CopyableCode code="api_blocked_prefixes" /> | `array` | A comma-separated list of endpoints and resources that are not allowed to be called from Snowflake. |
| <CopyableCode code="api_hook" /> | `object` |  |
| <CopyableCode code="comment" /> | `string` | Comment for the API integration. |
| <CopyableCode code="created_on" /> | `string` | Date and time when the API integration was created. |
| <CopyableCode code="enabled" /> | `boolean` | Whether the API integration is enabled. |

## Methods
| Name | Accessible by | Required Params | Optional Params | Description |
|:-----|:--------------|:----------------|:----------------|:------------|
| <CopyableCode code="fetch_api_integration" /> | `SELECT` | <CopyableCode code="name, endpoint" /> | - | Fetch an API integration |
| <CopyableCode code="list_api_integrations" /> | `SELECT` | <CopyableCode code="endpoint" /> | <CopyableCode code="like" /> | List API integrations |
| <CopyableCode code="create_api_integration" /> | `INSERT` | <CopyableCode code="data__api_allowed_prefixes, data__api_hook, data__enabled, data__name, endpoint" /> | <CopyableCode code="createMode" /> | Create an API integration |
| <CopyableCode code="delete_api_integration" /> | `DELETE` | <CopyableCode code="name, endpoint" /> | <CopyableCode code="ifExists" /> | Delete an API integration |
| <CopyableCode code="create_or_alter_api_integration" /> | `REPLACE` | <CopyableCode code="name, data__api_allowed_prefixes, data__api_hook, data__enabled, data__name, endpoint" /> | - | Create an (or alter an existing) API integration. Note that API_KEY is not currently altered by this operation and is supported for a newly-created object only. Unsetting API_BLOCKED_PREFIXES is also unsupported. |

<br />


<details>
<summary>Optional Parameter Details</summary>

| Name | Description | Type | Default |
|------|-------------|------|---------|
| <CopyableCode code="createMode" /> | Query parameter allowing support for different modes of resource creation. Possible values include: - `errorIfExists`: Throws an error if you try to create a resource that already exists. - `orReplace`: Automatically replaces the existing resource with the current one. - `ifNotExists`: Creates a new resource when an alter is requested for a non-existent resource. | `string` | `errorIfExists` |
| <CopyableCode code="ifExists" /> | Query parameter that specifies how to handle the request for a resource that does not exist: - `true`: The endpoint does not throw an error if the resource does not exist. It returns a 200 success response, but does not take any action on the resource. - `false`: The endpoint throws an error if the resource doesn't exist. | `boolean` | `false` |
| <CopyableCode code="like" /> | Query parameter to filter the command output by resource name. Uses case-insensitive pattern matching, with support for SQL wildcard characters. | `string` | `-` |

</details>

## `SELECT` examples

<Tabs
    defaultValue="list_api_integrations"
    values={[
        { label: 'list_api_integrations', value: 'list_api_integrations' },
        { label: 'fetch_api_integration', value: 'fetch_api_integration' }
    ]
}>
<TabItem value="list_api_integrations">

List API integrations

```sql
SELECT
name,
api_allowed_prefixes,
api_blocked_prefixes,
api_hook,
comment,
created_on,
enabled
FROM snowflake.api_integration.api_integrations
WHERE endpoint = '{{ endpoint }}';
```
</TabItem>
<TabItem value="fetch_api_integration">

Fetch an API integration

```sql
SELECT
name,
api_allowed_prefixes,
api_blocked_prefixes,
api_hook,
comment,
created_on,
enabled
FROM snowflake.api_integration.api_integrations
WHERE name = '{{ name }}'
AND endpoint = '{{ endpoint }}';
```
</TabItem>
</Tabs>

## `INSERT` example

Create an API integration

<Tabs
    defaultValue="all"
    values={[
        { label: 'Required Properties', value: 'required' },
        { label: 'All Properties', value: 'all', },
        { label: 'Manifest', value: 'manifest', },
    ]
}>
<TabItem value="all">

```sql
/*+ create */
INSERT INTO snowflake.api_integration.api_integrations (
data__name,
data__api_hook,
data__api_allowed_prefixes,
data__api_blocked_prefixes,
data__enabled,
data__comment,
endpoint
)
SELECT 
'{{ name }}',
'{{ api_hook }}',
'{{ api_allowed_prefixes }}',
'{{ api_blocked_prefixes }}',
{{ enabled }},
'{{ comment }}',
'{{ endpoint }}'
;
```
</TabItem>

<TabItem value="required">

```sql
/*+ create */
INSERT INTO snowflake.api_integration.api_integrations (
data__name,
data__api_hook,
data__api_allowed_prefixes,
data__enabled,
endpoint
)
SELECT 
'{{ name }}',
'{{ api_hook }}',
'{{ api_allowed_prefixes }}',
{{ enabled }},
'{{ endpoint }}'
;
```
</TabItem>

<TabItem value="manifest">

```yaml
# Description fields below are for documentation purposes only and are not required in the manifest
- name: api_integrations
  props:
    - name: endpoint
      value: string
      description: Required parameter for the api_integrations resource.
    - name: name
      value: string
      description: >-
        Name of the API integration. (Required parameter for the
        api_integrations resource.)
    - name: api_hook
      value:
        type: string
      description: Required parameter for the api_integrations resource.
    - name: api_allowed_prefixes
      value: array
      description: >-
        A comma-separated list of endpoints and resources that Snowflake can
        access. (Required parameter for the api_integrations resource.)
    - name: api_blocked_prefixes
      value: array
      description: >-
        A comma-separated list of endpoints and resources that are not allowed
        to be called from Snowflake.
    - name: enabled
      value: boolean
      description: >-
        Whether the API integration is enabled. (Required parameter for the
        api_integrations resource.)
    - name: comment
      value: string
      description: Comment for the API integration.
```
</TabItem>
</Tabs>

## `REPLACE` example

Create an (or alter an existing) API integration. Note that API_KEY is not currently altered by this operation and is supported for a newly-created object only. Unsetting API_BLOCKED_PREFIXES is also unsupported.

```sql
/*+ update */
REPLACE snowflake.api_integration.api_integrations
SET 
name = '{{ name }}',
api_hook = '{{ api_hook }}',
api_allowed_prefixes = '{{ api_allowed_prefixes }}',
api_blocked_prefixes = '{{ api_blocked_prefixes }}',
enabled = {{ enabled }},
comment = '{{ comment }}'
WHERE 
name = '{{ name }}'
AND data__api_allowed_prefixes = '{{ data__api_allowed_prefixes }}'
AND data__api_hook = '{{ data__api_hook }}'
AND data__enabled = '{{ data__enabled }}'
AND data__name = '{{ data__name }}'
AND endpoint = '{{ endpoint }}';
```

## `DELETE` example

Delete an API integration

```sql
/*+ delete */
DELETE FROM snowflake.api_integration.api_integrations
WHERE name = '{{ name }}'
AND endpoint = '{{ endpoint }}';
```
