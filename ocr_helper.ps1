param (
    [Parameter(Mandatory=$true)]
    [string]$ImagePath
)

try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.Drawing

    $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    }

    function Await-WinRT($asyncOp, $type) {
        $method = $asTaskGeneric.MakeGenericMethod($type)
        $task = $method.Invoke($null, @($asyncOp))
        $task.Wait()
        return $task.Result
    }

    [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime] | Out-Null
    [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime] | Out-Null

    $fullPath = [System.IO.Path]::GetFullPath($ImagePath)
    $fileBytes = [System.IO.File]::ReadAllBytes($fullPath)
    $memStream = New-Object System.IO.MemoryStream(,$fileBytes)

    # Convert to WinRT IRandomAccessStream
    $winrtStream = [System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($memStream)

    $asyncOp = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($winrtStream)
    $decoder = Await-WinRT $asyncOp ([Windows.Graphics.Imaging.BitmapDecoder])

    $asyncOp = $decoder.GetSoftwareBitmapAsync()
    $bitmap = Await-WinRT $asyncOp ([Windows.Graphics.Imaging.SoftwareBitmap])

    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($null -eq $engine) {
        $lang = [Windows.Globalization.Language]::new('en-US')
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
    }

    $asyncOp = $engine.RecognizeAsync($bitmap)
    $result = Await-WinRT $asyncOp ([Windows.Media.Ocr.OcrResult])

    if ($result -and $result.Text) {
        Write-Output $result.Text
    }
} catch {
    Write-Error $_.Exception.ToString()
    exit 1
}
