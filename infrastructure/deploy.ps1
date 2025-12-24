param(
    [Parameter(Mandatory=$true)][string]$ResourceGroup,
    [Parameter(Mandatory=$true)][string]$TemplateFile,
    [Parameter(Mandatory=$true)][string]$ParametersFile
)

az deployment group create `
    --resource-group $ResourceGroup `
    --template-file $TemplateFile `
    --parameters @$ParametersFile
