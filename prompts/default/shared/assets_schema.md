### assets table

| Column | Description |
|--------|-------------|
| asset_id | Unique identifier for each asset |
| approval_status | Status of the asset approval process |
| approved_at | Timestamp when the asset was approved |
| asset_description | Description of the asset |
| asset_filepath | Location of storage (e.g., GCS Path, On-prem Parquet location) |
| asset_name | Name of the asset |
| business_function | Business function that owns the asset |
| data_product_owner | Owner of the asset |
| created_at | Asset onboarded timestamp to LDC/Fabric |
| created_by | Asset onboarded by to LDC/Fabric |
| data_asset_status | Status in pipeline (e.g., Live, In progress) |
| data_asset_type | Type of asset (e.g., MRDS, PRI, MDA, GDA, CDA) |
| data_domain | Value stream/data domain where data is created |
| data_format | Output format (e.g., Delta, Parquet, BQ Table, Hive Table) |
| data_virtualized | Boolean: is the asset a data product |
| delivery_team | Team responsible for delivering the asset |
| high_level_solution_design_approved | Boolean: is the HLSD approved |
| intermediary_asset | Boolean: is this an intermediary asset |
| ldc_status | LDC/Fabric lifecycle status (e.g., REGISTERED, DRAFT) |
| physical_name | Physical location of the asset |
| platform | Platform where the asset is hosted |
| platform_cin_id | CIN ID of the hosting platform |
| refresh_day | Day of refresh (e.g., Monday, Everyday, 1st Day) |
| refresh_frequency | Frequency (e.g., Daily, Weekly, Monthly) |
| strategic_data_asset | Boolean: is this a strategic data asset |
| updated_at | Last update timestamp |
| updated_by | Last update made by |
| value_stream | Value stream/data domain where data is created |
