---
title: future_grants
hide_title: false
hide_table_of_contents: false
keywords:
  - future_grants
  - database_role
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

Creates, updates, deletes, gets or lists a <code>future_grants</code> resource.

## Overview
<table><tbody>
<tr><td><b>Name</b></td><td><code>future_grants</code></td></tr>
<tr><td><b>Type</b></td><td>Resource</td></tr>
<tr><td><b>Id</b></td><td><CopyableCode code="snowflake.database_role.future_grants" /></td></tr>
</tbody></table>

## Fields
| Name | Datatype | Description |
|:-----|:---------|:------------|
| <CopyableCode code="containing_scope" /> | `object` |  |
| <CopyableCode code="created_on" /> | `string` | Date and time when the grant was created |
| <CopyableCode code="grant_option" /> | `boolean` | If true, allows the recipient role to grant the privileges to other roles. |
| <CopyableCode code="granted_by" /> | `string` | The role that granted this privilege to this grantee |
| <CopyableCode code="privileges" /> | `array` | List of privileges to be granted. |
| <CopyableCode code="securable" /> | `object` |  |
| <CopyableCode code="securable_type" /> | `string` | Type of the securable to be granted. |

## Methods
| Name | Accessible by | Required Params | Optional Params | Description |
|:-----|:--------------|:----------------|:----------------|:------------|
| <CopyableCode code="list_future_grants" /> | `SELECT` | <CopyableCode code="database_name, name, endpoint" /> | <CopyableCode code="showLimit" /> | List all future grants to the role |
| <CopyableCode code="grant_future_privileges" /> | `INSERT` | <CopyableCode code="database_name, name, data__securable_type, endpoint" /> | - | Grant future privileges to the role |
| <CopyableCode code="revoke_future_grants" /> | `DELETE` | <CopyableCode code="database_name, name, data__securable_type, endpoint" /> | <CopyableCode code="mode" /> | Revoke future grants from the role |

<br />


<details>
<summary>Optional Parameter Details</summary>

| Name | Description | Type | Default |
|------|-------------|------|---------|
| <CopyableCode code="mode" /> | Query parameter determines whether the revoke operation succeeds or fails for the privileges, based on the whether the privileges had been re-granted to another role. - restrict: If the privilege being revoked has been re-granted to another role, the REVOKE command fails. - cascade: If the privilege being revoked has been re-granted, the REVOKE command recursively revokes these dependent grants. If the same privilege on an object has been granted to the target role by a different grantor (parallel grant), that grant is not affected and the target role retains the privilege. | `string` | `-` |
| <CopyableCode code="showLimit" /> | Query parameter to limit the maximum number of rows returned by a command. | `integer` | `-` |

</details>

## `SELECT` examples

List all future grants to the role


```sql
SELECT
containing_scope,
created_on,
grant_option,
granted_by,
privileges,
securable,
securable_type
FROM snowflake.database_role.future_grants
WHERE database_name = '{{ database_name }}'
AND name = '{{ name }}'
AND endpoint = '{{ endpoint }}';
```
## `INSERT` example

Grant future privileges to the role

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
INSERT INTO snowflake.database_role.future_grants (
data__securable,
data__containing_scope,
data__securable_type,
data__grant_option,
data__privileges,
database_name,
name,
endpoint
)
SELECT 
'{{ securable }}',
'{{ containing_scope }}',
'{{ securable_type }}',
{{ grant_option }},
'{{ privileges }}',
'{{ database_name }}',
'{{ name }}',
'{{ endpoint }}'
;
```
</TabItem>

<TabItem value="required">

```sql
/*+ create */
INSERT INTO snowflake.database_role.future_grants (
data__securable_type,
database_name,
name,
endpoint
)
SELECT 
'{{ securable_type }}',
'{{ database_name }}',
'{{ name }}',
'{{ endpoint }}'
;
```
</TabItem>

<TabItem value="manifest">

```yaml
# Description fields below are for documentation purposes only and are not required in the manifest
- name: future_grants
  props:
    - name: database_name
      value: string
      description: Required parameter for the future_grants resource.
    - name: name
      value: string
      description: Required parameter for the future_grants resource.
    - name: endpoint
      value: string
      description: Required parameter for the future_grants resource.
    - name: securable
      value:
        database: string
        schema: string
        service: string
        name: string
    - name: containing_scope
      value:
        database: string
        schema: string
    - name: securable_type
      value: string
      description: >-
        Type of the securable to be granted. (Required parameter for the
        future_grants resource.)
    - name: grant_option
      value: boolean
      description: >-
        If true, allows the recipient role to grant the privileges to other
        roles.
    - name: privileges
      value: array
      description: List of privileges to be granted.
```
</TabItem>
</Tabs>

## `DELETE` example

Revoke future grants from the role

```sql
/*+ delete */
DELETE FROM snowflake.database_role.future_grants
WHERE database_name = '{{ database_name }}'
AND name = '{{ name }}'
AND data__securable_type = '{{ data__securable_type }}'
AND endpoint = '{{ endpoint }}';
```
