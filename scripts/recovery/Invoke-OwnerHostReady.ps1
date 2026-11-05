[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$command=Get-Command tailscale.exe -ErrorAction SilentlyContinue
$client=if($command){$command.Source}else{Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'}
if(-not (Test-Path -LiteralPath $client)){throw 'Tailscale client unavailable; stop without changing SSH security.'}
$status=(& $client status --json)|ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $status.BackendState -ne 'Running'){throw 'Tailscale is not running.'}
$peers=@($status.Peer.PSObject.Properties.Value|Where-Object HostName -eq 'homelab')
if($peers.Count -ne 1 -or -not $peers[0].Online){throw 'Exactly one online homelab peer is required.'}
$addresses=@($peers[0].TailscaleIPs|Where-Object {$_ -match '^100\.'})
if($addresses.Count -ne 1){throw 'No unique verified peer IPv4 address.'}
$address=[Net.IPAddress]::Parse($addresses[0])
$bytes=$address.GetAddressBytes()
if($bytes.Length -ne 4 -or $bytes[0] -ne 100 -or $bytes[1] -lt 64 -or $bytes[1] -gt 127){throw 'Peer address outside Tailscale IPv4 range.'}
$repo=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$script=Join-Path $repo 'scripts\recovery\finalize_host_24x7.sh'
if(-not (Test-Path -LiteralPath $script)){throw 'finalize_host_24x7.sh not found in this checkout.'}
$remote='/tmp/finalize_host_24x7.sh'
'Finalizing 24/7 host settings (logind no-suspend + SSH-safe UFW). No storage or package change. Owner sudo required; stop after any failure.'
& scp -o "Hostname=$address" -o HostKeyAlias=homelab -o StrictHostKeyChecking=yes $script "mew@homelab:$remote"
if($LASTEXITCODE -ne 0){throw 'Upload failed; nothing executed on the host.'}
& ssh -t -o "Hostname=$address" -o HostKeyAlias=homelab -o StrictHostKeyChecking=yes mew@homelab "sudo bash $remote; rc=`$?; rm -f $remote; exit `$rc"
exit $LASTEXITCODE
