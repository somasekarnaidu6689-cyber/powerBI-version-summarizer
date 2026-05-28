## error faced 
```
PS C:\Users\somsekar.naidu\Desktop\projects> .\.venv\Scripts\activate         
.\.venv\Scripts\activate : File C:\Users\somsekar.naidu\Desktop\projects\.venv\Scripts\Activate.ps1 cannot be loaded because running 
scripts is disabled on this system. For more information, see about_Execution_Policies at 
https:/go.microsoft.com/fwlink/?LinkID=135170.
At line:1 char:1
+ .\.venv\Scripts\activate
+ ~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : SecurityError: (:) [], PSSecurityException
    + FullyQualifiedErrorId : UnauthorizedAccess
```
## walkaround
```
PS C:\Users\somsekar.naidu\Desktop\projects> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
PS C:\Users\somsekar.naidu\Desktop\projects> .\.venv\Scripts\activate       
```
<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->
