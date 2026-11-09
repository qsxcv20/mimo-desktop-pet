# Trim transparent PNG to its alpha bounding box, then fit into a square canvas
# aligned with the dsh-whale-widget 610x610 pet asset spec.
param(
  [Parameter(Mandatory = $true)][string]$Src,
  [Parameter(Mandatory = $true)][string]$Out,
  [int]$Size = 610,
  [string]$Preview
)

Add-Type -AssemblyName System.Drawing

function Get-AlphaBBox($bmp) {
  $tw = 256; $th = 256
  $thumb = New-Object System.Drawing.Bitmap $tw, $th, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $gt = [System.Drawing.Graphics]::FromImage($thumb)
  $gt.Clear([System.Drawing.Color]::Transparent)
  $gt.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $gt.DrawImage($bmp, 0, 0, $tw, $th)
  $gt.Dispose()
  $minX = $tw; $minY = $th; $maxX = -1; $maxY = -1
  for ($y = 0; $y -lt $th; $y++) {
    for ($x = 0; $x -lt $tw; $x++) {
      if ($thumb.GetPixel($x, $y).A -gt 10) {
        if ($x -lt $minX) { $minX = $x }; if ($x -gt $maxX) { $maxX = $x }
        if ($y -lt $minY) { $minY = $y }; if ($y -gt $maxY) { $maxY = $y }
      }
    }
  }
  $thumb.Dispose()
  return @{ minX = $minX; minY = $minY; maxX = $maxX; maxY = $maxY; sx = ($bmp.Width / $tw); sy = ($bmp.Height / $th) }
}

$src = [System.Drawing.Bitmap]::FromFile($Src)
$bb = Get-AlphaBBox $src
$minX = [int]($bb.minX * $bb.sx); $minY = [int]($bb.minY * $bb.sy)
$maxX = [int](($bb.maxX + 1) * $bb.sx); $maxY = [int](($bb.maxY + 1) * $bb.sy)
$cw = $maxX - $minX + 1; $ch = $maxY - $minY + 1
$pad = [int]($cw * 0.02)
$minX = [Math]::Max(0, $minX - $pad); $minY = [Math]::Max(0, $minY - $pad)
$maxX = [Math]::Min($src.Width, $maxX + $pad); $maxY = [Math]::Min($src.Height, $maxY + $pad)
$cw = $maxX - $minX; $ch = $maxY - $minY

$dst = New-Object System.Drawing.Bitmap $Size, $Size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($dst)
$g.Clear([System.Drawing.Color]::Transparent)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
$scale = [Math]::Min($Size / $cw, $Size / $ch)
$dw = [int]($cw * $scale); $dh = [int]($ch * $scale)
$dx = [int](($Size - $dw) / 2); $dy = $Size - $dh
$g.DrawImage($src, (New-Object System.Drawing.Rectangle $dx, $dy, $dw, $dh), $minX, $minY, $cw, $ch, [System.Drawing.GraphicsUnit]::Pixel)
$g.Dispose()
$dst.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$dst.Dispose()

if ($Preview) {
  $pv = New-Object System.Drawing.Bitmap 160, 160, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g2 = [System.Drawing.Graphics]::FromImage($pv)
  $g2.Clear([System.Drawing.Color]::FromArgb(255, 255, 255, 255))
  $g2.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g2.DrawImage([System.Drawing.Image]::FromFile($Out), 0, 0, 160, 160)
  $g2.Dispose(); $pv.Save($Preview, [System.Drawing.Imaging.ImageFormat]::Png); $pv.Dispose()
}
$src.Dispose()
Write-Output ("{0}  content {1}x{2} -> {3}x{4}" -f (Split-Path $Out -Leaf), $cw, $ch, $dw, $dh)
