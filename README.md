Efficiently load and manipulate gene regulatory networks in Python. Built for [our collection of network data](https://github.com/ekernf01/network_collection).

This module defines a `LightNetwork` object. This is a thin wrapper around duckdb, which is used to query Parquet files (on disk), Pandas DataFrames (in memory), or some combination thereof. The main purpose is to avoid copying/instantiating a whole database of network edges in RAM. Instead we just store the names of relevant files on disk, and we read individual records as needed. See the network collection to learn how the data are formatted or how to add your own networks.

### Installation

pip install git+https://github.com/ekernf01/pereggrn_networks.git

### Usage

```python
import pereggrn_networks
# Set this to point to the "networks" folder in the network collection. 
pereggrn_networks.set_grn_path("path/to/network_collection/networks")
# What networks are available?
pereggrn_networks.load_grn_metadata()
# What tissues do they cover, or how many?
pereggrn_networks.list_subnetworks("gtex_rna")
[ pereggrn_networks.list_subnetworks(n)[0] for n in pereggrn_networks.load_grn_metadata()['name'] ]
# Show me the edges for a tissue (as a Pandas dataframe). 
pereggrn_networks.load_grn_by_subnetwork("gtex_rna", "Adipose_Subcutaneous.parquet").head()
# Show me the edges for all tissues in one network (as a Pandas dataframe).
[pereggrn_networks.load_grn_by_subnetwork("gtex_rna", n).shape for n in pereggrn_networks.list_subnetworks('gtex_rna') ]
# Query the edges for a tissue (as a lightweight, read-only interface, without loading the edges into memory)
pereggrn_networks.LightNetwork("gtex_rna").get_regulators("GAPDH")
pereggrn_networks.LightNetwork("gtex_rna", ["Adipose_Subcutaneous.parquet"]).get_regulators("GAPDH")
# Create a new LightNetwork object from your own parquet files or pandas dataframes
import pandas as pd
pereggrn_networks.LightNetwork(df = pd.DataFrame({"regulator": ["a"], "target": ["b"], "weight": [-1]}))
pereggrn_networks.LightNetwork(files = ["path/to/my/network.parquet","path/to/my/other/network.parquet"])
help(pereggrn_networks.LightNetwork)
```

