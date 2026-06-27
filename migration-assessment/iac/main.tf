terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}

# ── Variables ────────────────────────────────────────────────────────────────
variable "resource_group" { default = "rg-petclinic-migration" }
variable "location"       { default = "southeastasia" }
variable "cluster_name"   { default = "aks-petclinic-prod" }
variable "acr_name"       { default = "acrpetclinicprod" }

# ── Resource Group ───────────────────────────────────────────────────────────
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group
  location = var.location
  tags     = { project = "rancher-to-aks", environment = "production" }
}

# ── Azure Container Registry ─────────────────────────────────────────────────
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Standard"
  admin_enabled       = false
  tags                = { project = "rancher-to-aks" }
}

# ── AKS Cluster ──────────────────────────────────────────────────────────────
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "petclinic-aks"
  kubernetes_version  = "1.28"

  # System node pool — for kube-system workloads only
  default_node_pool {
    name                = "system"
    node_count          = 1
    vm_size             = "Standard_D2s_v3"
    os_disk_size_gb     = 50
    type                = "VirtualMachineScaleSets"
    only_critical_addons_enabled = true    # taint: CriticalAddonsOnly
    node_labels = { "nodepool-type" = "system" }
  }

  # Managed identity — no service principal needed
  identity {
    type = "SystemAssigned"
  }

  # Azure CNI powered by Cilium — required for CiliumNetworkPolicy
  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"       # required for Cilium
    network_data_plane   = "cilium"        # enables Cilium CNI
    outbound_type       = "managedNATGateway"  # fixed egress IP for partner allowlists
    load_balancer_sku   = "standard"
  }

  # Key Vault integration via Secret Store CSI Driver
  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  # Workload identity — replaces service principal in pods
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  # Azure Monitor / Container Insights
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  }

  tags = { project = "rancher-to-aks", environment = "production" }
}

# ── User node pool — application workloads ───────────────────────────────────
resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "userpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_D4s_v3"
  node_count            = 2
  enable_auto_scaling   = true
  min_count             = 2
  max_count             = 5
  os_disk_size_gb       = 100
  node_labels           = { "nodepool-type" = "user" }
  node_taints           = []
  tags                  = { project = "rancher-to-aks" }
}

# ── Log Analytics Workspace ──────────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-petclinic-migration"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# ── ACR pull permission for AKS ──────────────────────────────────────────────
resource "azurerm_role_assignment" "acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}

# ── Outputs ──────────────────────────────────────────────────────────────────
output "aks_name"           { value = azurerm_kubernetes_cluster.aks.name }
output "acr_login_server"   { value = azurerm_container_registry.acr.login_server }
output "resource_group"     { value = azurerm_resource_group.rg.name }
output "get_credentials_cmd" {
  value = "az aks get-credentials --resource-group ${var.resource_group} --name ${var.cluster_name}"
}

# ── Virtual Network & Subnets ────────────────────────────────────────────────
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-petclinic-migration"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = ["10.1.0.0/16"]
}

resource "azurerm_subnet" "aks_system" {
  name                 = "aks-system-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.1.0.0/24"]
}

resource "azurerm_subnet" "aks_user" {
  name                 = "aks-user-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.1.1.0/23"]
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "private-endpoint-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.1.4.0/28"]
}

# ── Azure Key Vault ──────────────────────────────────────────────────────────
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "kv" {
  name                        = "kv-petclinic-prod"
  location                    = azurerm_resource_group.rg.location
  resource_group_name         = azurerm_resource_group.rg.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  soft_delete_retention_days  = 90
  purge_protection_enabled    = true

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }
}

# Private endpoint for Key Vault
resource "azurerm_private_endpoint" "kv_pe" {
  name                = "pe-keyvault-petclinic"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints.id

  private_service_connection {
    name                           = "kv-connection"
    private_connection_resource_id = azurerm_key_vault.kv.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }
}

# ── NAT Gateway for fixed egress IP ──────────────────────────────────────────
resource "azurerm_public_ip" "nat_pip" {
  name                = "pip-nat-petclinic"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]
}

resource "azurerm_nat_gateway" "nat" {
  name                    = "nat-petclinic-prod"
  location                = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name
  sku_name                = "Standard"
  idle_timeout_in_minutes = 10
}

resource "azurerm_nat_gateway_public_ip_association" "nat_pip" {
  nat_gateway_id       = azurerm_nat_gateway.nat.id
  public_ip_address_id = azurerm_public_ip.nat_pip.id
}

output "nat_gateway_public_ip" {
  value       = azurerm_public_ip.nat_pip.ip_address
  description = "Fixed egress IP — add this to partner bank API allowlists"
}
