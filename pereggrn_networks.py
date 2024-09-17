import pandas as pd 
import duckdb
import os 
import gc
import numpy as np

EXPECTED_GRN_COLNAMES = ["regulator", "target", "weight"]


class LightNetwork:
  """
  The LightNetwork class is a lightweight, read-only interface to our database of weighted TF-target interactions.
  It supports just a few simple operations -- for now, just querying with a target and returning
  relevant TF's and weights. 
  Under the hood, it uses duckdb to query parquet files, so data are not loaded into RAM. 
  """
  def __init__(
    self,
    grn_name: str = None,
    subnetwork_names: list = [],
    files:list = [],
    df: pd.DataFrame = None,
  ):
    """Create a LightNetwork object. 

    Args:
        grn_name (str, optional): source of networks, e.g. "celloracle_human"
        subnetwork_name (list, optional): filename for individual network (usually networks are grouped by cell/tissue type).
            If the empty list is passed, all available subnetworks will be used.
        files (list, optional): List of absolute paths to parquet files. 
            These files will be queried in addition to the stuff already specified.
        df (pd.DataFrame, optional): This DF will be queried in addition to the stuff already specified.
    """
    assert isinstance(subnetwork_names, list), "subnetwork_names must be a list, even if it only contains one item."
    if grn_name is None and len(subnetwork_names) > 0:
      raise ValueError("Cannot find subnetworks unless 'grn_name' is specified.")
    if grn_name is not None:
      if len(subnetwork_names) == 0:
        subnetwork_names = list_subnetworks(grn_name)
      files = files + [os.path.join(os.environ["GRN_PATH"], grn_name, "networks", s) for s in subnetwork_names]
    if len(files) == 0 and df is None:
      raise ValueError("Please provide at least one of 'grn_name' or 'files' of 'df'.")
    if df is not None:
      assert all(df.columns[0:3] == ['regulator', 'target', 'weight'] ), "Columns must have names 'regulator', 'target', 'weight'"
      assert len(df.columns)==3 or df.columns[3]=='cell_type', "If there are 4 columns, the 4th must be 'cell_type'."
    self.files = files
    self.df = df
    for f in self.files:
      if not os.path.exists(f):
        raise FileNotFoundError(f"File {f} does not exist.")
    return

  def __str__(self):
      files_report = ""
      df_report = ""
      if len(self.files) > 0:
          files_report = "\n files: \n" + '\n  '.join(self.files)
      if self.df is not None:
          df_report = f"\n dataframe of shape {self.df.shape}"
      return "LightNetwork built on " + files_report + df_report

  def copy(self):
    return LightNetwork(files = self.files, df = self.df)

  def save(self, filename) -> None:
    if not filename.lower().endswith(".parquet"):
      raise ValueError("Filename must end with .parquet.")
    self.get_all().to_parquet(filename)
    return

  def get_all(self):
    results_from_parquet = pd.DataFrame()
    results_from_memory  = pd.DataFrame()
    if len(self.files) > 0:
      files_formatted = [f"'{file}'" for file in self.files]
      results_from_parquet = duckdb.query(
        " UNION ".join(
            [
              f"SELECT * FROM {file}" for file in files_formatted
            ]
          )
      ).df()
    if not self.df is None:
      con = duckdb.connect()
      df=self.df
      results_from_memory = con.execute(f"SELECT * FROM df").df()
    return pd.concat([results_from_parquet, results_from_memory])

  def get_regulators(self, target: str) -> pd.DataFrame: 
    """Return all records having a given target gene.

    Args:
        target (str): A target gene present in this network. 

    Returns:
        pd.DataFrame: All records with the given target gene
    """
    results_from_parquet = pd.DataFrame()
    results_from_memory  = pd.DataFrame()
    if len(self.files) > 0:
      files_formatted = [f"'{file}'" for file in self.files]
      results_from_parquet = duckdb.query(
        " UNION ".join(
            [
              f"SELECT * FROM {file} WHERE target = '{target}'" for file in files_formatted
            ]
          )
      ).df()
    if not self.df is None:
      con = duckdb.connect()
      df=self.df
      results_from_memory = con.execute(f"SELECT * FROM df WHERE target = '{target}'").df()
    return pd.concat([results_from_parquet, results_from_memory])
  
  def get_targets(self, regulator: str) -> pd.DataFrame: 
    """Return all records having a given regulator.

    Args:
        regulator (str): A regulator present in this network. 

    Returns:
        pd.DataFrame: All records with the given regulator
    """
    results_from_parquet = pd.DataFrame()
    results_from_memory  = pd.DataFrame()
    if len(self.files) > 0:
      files_formatted = [f"'{file}'" for file in self.files]
      results_from_parquet = duckdb.query(
        " UNION ".join(
            [
              f"SELECT * FROM {file} WHERE regulator = '{regulator}'" for file in files_formatted
            ]
          )
      ).df()
    if not self.df is None:
      con = duckdb.connect()
      df=self.df
      results_from_memory = con.execute(f"SELECT * FROM df WHERE regulator = '{regulator}'").df()
    return pd.concat([results_from_parquet, results_from_memory])
    
  def get_all_regulators(self) -> set: 
    """Return a set of all regulators

    Returns:
        set: All distinct regulators
    """
    return self.get_all_one_field("regulator")

  def get_all_one_field(self, field: str) -> set: 
    """Return a set of all regulators, or all targets, or all cell types.

    Returns:
        set: All distinct values listed in a given column from this network
    """
    assert field in {"regulator", "target", "cell_type"}, " Can only get unique vals for 'regulator', 'target', or 'cell_type' "
    results_from_parquet = pd.DataFrame(columns = [field])
    results_from_memory  = pd.DataFrame(columns = [field])
    if len(self.files) > 0:
      files_formatted = [f"'{file}'" for file in self.files]
      files_formatted = [
        file for file in files_formatted 
        if field in set(duckdb.query(f"SELECT * FROM {file} WHERE 1=0").df().columns)
      ]
      if len(files_formatted) > 0:
        results_from_parquet = duckdb.query(
          " UNION ".join(
              [
                f"SELECT DISTINCT {field} FROM {file}" for file in files_formatted
              ]
            )
        ).df()
    if not self.df is None and field in set(self.df.columns):
      con = duckdb.connect()
      df=self.df
      results_from_memory = con.execute(f"SELECT DISTINCT {field} FROM df").df()
    return set(pd.concat([results_from_parquet, results_from_memory])[field].unique())
    
  def get_num_edges(self) -> int: 
    """Return the number of available regulator-target connections.
    This assumes no overlap between edges recorded in 'files' and stuff provided in 'df'.

    Returns:
        int
    """
    results_from_parquet = 0
    results_from_memory  = 0
    if len(self.files) > 0:
      files_formatted = [f"'{file}'" for file in self.files]
      results_from_parquet = duckdb.query(
        "SELECT COUNT(*) FROM " + \
        "( " + \
          " UNION ".join(
              [
                f"SELECT * FROM {file}" for file in files_formatted
              ]
            ) + \
        " )"
      ).df().iloc[0,0]
    if not self.df is None:
      con = duckdb.connect()
      df=self.df
      results_from_memory = con.execute("SELECT COUNT(*) FROM df").df().iloc[0,0]
    return int(results_from_parquet + results_from_memory)
    
def load_grn_metadata( complete_only = True ):
  """Load metadata on GRN sources."""
  try:
      metadata_df = pd.read_csv(os.path.join(os.environ["GRN_PATH"], "published_networks.csv"))
  except (KeyError,FileNotFoundError):
      raise FileNotFoundError("Network data files not found. Please run load_networks.debug_grn_location().")
  metadata_df.index = metadata_df["name"]
  if complete_only: 
    metadata_df = metadata_df.loc[metadata_df['is_ready'] == "yes",:]
  return metadata_df

def list_subnetworks(grn_name: str):
  """
  List all tissues available from a given source. 
  Parameters:
        - grn_name (string) source to list tissues from
  Return value: pd.DataFrame
  """
  try:
    subnets = [f for f in os.listdir(os.path.join(os.environ["GRN_PATH"], grn_name, "networks")) if not f.startswith('.')]
  except (KeyError,FileNotFoundError):
    raise FileNotFoundError("Network data files not found. Try checking: \n- pereggrn_networks.load_grn_metadata() or pereggrn_networks.list_subnetworks() for network names, \n- pereggrn_networks.debug_grn_location() or pereggrn_networks.set_grn_path() for the path to the collection.")
  return subnets


def debug_grn_location(path=None):
  if path is None:
    path = get_grn_location()

  print(f"""
    GRN location is currently set to {path}.
    Set it using load_networks.set_grn_location().
    This package expects a folder structure like this:
    > tree networks
    networks
    ├── published_networks.csv 
    ├── ANANSE_tissue_0.8
    │   └── networks
    │       ├── adrenal_gland.parquet
    │       ├── bone_marrow.parquet
    │       ├── brain.parquet
    │       ├── cervix.parquet
    |       ...
    ├── cellnet_human_Hg1332
    │   └── networks
    │       ├── bcell.parquet
    │       ├── colon.parquet
    │       ├── esc.parquet
    |       ...
""")
  print(f"Validating this structure is not yet automated but you can manually compare to `tree {path}`. ")
  return

def get_grn_location():
  return os.environ['GRN_PATH']
   
def set_grn_location(path: str):
  if not os.path.isfile(os.path.join(path, "published_networks.csv")):
    raise FileNotFoundError("published_networks.csv is missing. Try load_networks.debug_grn_location() for more help.")
  if not os.path.isfile(os.path.join(path, "cellnet_human_Hg1332", "networks", "bcell.parquet")):
    print("Checked for an example network and didn't find it; this is a bad sign. Try debug_grn_location() for more help.")
  os.environ['GRN_PATH'] = path
  return


def load_grn_by_subnetwork( grn_name: str, subnetwork_name: str ):
  """
  Load a given gene regulatory (sub-)network.
  Parameters:
        - grn_name (str): source to list tissues from
        - subnetwork_name (str): what subnetwork to use; see list_subnetworks(grn_name) for options
  """
  grn_location = os.path.join(get_grn_location(), grn_name, "networks", subnetwork_name)
  if not os.path.exists(grn_location):
    raise FileNotFoundError("Network data files not found. Try checking: \n- pereggrn_networks.load_grn_metadata() or pereggrn_networks.list_subnetworks() for network names, \n- pereggrn_networks.debug_grn_location() or pereggrn_networks.set_grn_path() for the path to the collection.")

  X = pd.read_parquet( grn_location ) 
  
  # add score of -1 if missing
  if(X.shape[1] == 2):
    X["weight"] = -1
  
  X.set_axis(EXPECTED_GRN_COLNAMES, axis = 1, copy = False)
  # This saves mem for fat networks.
  X[EXPECTED_GRN_COLNAMES[0]].astype("category")
  X[EXPECTED_GRN_COLNAMES[1]].astype("category")
  return X 

def load_grn_all_subnetworks(grn_name):
  return pd.concat(
      [load_grn_by_subnetwork(grn_name, s) for s in list_subnetworks(grn_name)]
   )
    
def validate_grn(
  grn_name,
  subnetwork_name, 
  grn_df = None
):
  """Make sure grn conforms to the expected structure."""
  if grn_df is None:
    grn_df = load_grn_by_subnetwork( grn_name, subnetwork_name, do_validate=False )
  if len(grn_df[:, "regulator"].unique()) > len(grn_df[:, "target"].unique()):
    raise ValueError("".join([grn_name, " ", subnetwork_name, " has more regulators than targets!\n"]) )
  assert type(grn_df) == pd.DataFrame
  assert all( [grn_df.columns[i] == EXPECTED_GRN_COLNAMES[i] for i in range(3)])
  return True

def pivotNetworkLongToWide(networkEdges, regulatorColumn=0, targetColumn=1):
    """Reformat a network from a two-column dataframe to the way that celloracle needs its input.

    Args: 
        network_long (pd.DataFrame): GRN structure with columns ['regulator', 'target', 'weight']
    """
    X = pd.crosstab(networkEdges.iloc[:,targetColumn], networkEdges.iloc[:,regulatorColumn])
    del networkEdges
    gc.collect()
    X = 1.0*(X > 0)
    X = X.rename_axis('gene_short_name').reset_index()
    X = X.rename_axis('peak_id').reset_index()
    gc.collect()
    return X

def pivotNetworkWideToLong(network_wide: pd.DataFrame):
    """Convert from CellOracle's preferred format to a triplet format

    Args:
        network_wide (pd.DataFrame): GRN structure in CellOracle's usual format
    """
    network_long = pd.concat([
        pd.DataFrame({
            "regulator": tf,
            "target": network_wide.loc[network_wide[tf]==1, "gene_short_name"],
            "weight": 1,
        })
        for tf in network_wide.columns[2:]
    ])
    return network_long

def makeRandomNetwork(targetGenes, TFs, density = 0, seed = 0):
    """Generate a random network formatted the way that celloracle needs its input."""
    np.random.seed(seed)
    X = pd.DataFrame(
            np.random.binomial(
                n = 1, 
                p=density,
                size=(
                    len(targetGenes), 
                    len(TFs)
                )
            ),
            columns = TFs, 
            index = targetGenes
        )
    X.rename_axis('gene_short_name', inplace=True)
    X.reset_index(inplace=True)
    X.rename_axis('peak_id', inplace=True)
    X.reset_index(inplace=True)
    gc.collect()
    return X

def makeNetworkSparse(network_wide, defaultValue):
    """Save memory by making a sparse representation of a CellOracle-format base network"""
    network_wide.iloc[:,2:] = network_wide.iloc[:,2:].astype(pd.SparseDtype("float", defaultValue))
    return network_wide


def makeNetworkDense(network_wide):
    """Undo makeNetworkSparse"""
    network_wide.iloc[:, 2:] = np.array(network_wide.iloc[:, 2:])   #undo sparse representation         
    return network_wide