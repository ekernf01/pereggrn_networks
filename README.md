Efficiently load and manipulate gene regulatory networks in Python. Built for [our collection of network data](https://github.com/ekernf01/network_collection).

### Usage

```
# Set this to point to the "load_networks" folder inside the "networks" folder adjacent to this README. 
sys.path.append('path/to/load_networks/') 
import load_networks
# Set this to point to the "networks" folder adjacent to this README. 
os.environ["GRN_PATH"] = "networks"
# What networks are available?
load_networks.load_grn_metadata()
# What tissues do they cover, or how many?
load_networks.list_subnetworks("gtex_rna")
[ load_networks.list_subnetworks(n)[0] for n in load_networks.load_grn_metadata()['name'] ]
# Show me the edges for a tissue. 
load_networks.load_grn_by_subnetwork("gtex_rna", "Adipose_Subcutaneous.parquet").head()
# Show me the edges for all tissues in one network.
[load_networks.load_grn_by_subnetwork("gtex_rna", n).shape for n in load_networks.list_subnetworks('gtex_rna') ]
# Lightweight API
load_networks.LightNetwork("gtex_rna").get_regulators("GAPDH")
load_networks.LightNetwork("gtex_rna", ["Adipose_Subcutaneous.parquet"]).get_regulators("GAPDH")
```

