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
'Running corrected v2: explicit disk topology and the same one-attempt guards. Enter sudo password only in the SSH terminal. Stop after any failure.'
# Uses the live peer address if MagicDNS is unavailable, retaining the existing
# homelab host-key identity and strict checking. No trust/authentication bypass.
& ssh -t -o "Hostname=$address" -o HostKeyAlias=homelab -o StrictHostKeyChecking=yes mew@homelab bash /home/mew/.local/share/homelab-clean-20261105-v2/run-owner-clean.sh
exit $LASTEXITCODE
