using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Net.Http.Headers;
using Microsoft.Win32; // For OpenFileDialog
using System.IO; // For Directory and File operations
using System.Linq; // For FirstOrDefault
using System.Diagnostics; // For Debug.WriteLine
using System.Text.RegularExpressions; // For parsing imports
using System.Text.Json; // For JsonException
using System.Reflection;
using System.Windows.Media; // For SolidColorBrush

namespace dependencyfinder
{
    public partial class MainWindow : Window
    {
        private readonly HttpClient _httpClient = new(new HttpClientHandler
        {
            AutomaticDecompression = System.Net.DecompressionMethods.GZip | System.Net.DecompressionMethods.Deflate
        });
        private string? _selectedLanguage;
        private string? _selectedFolderPath;
        private string? _selectedFilePath; // Store the full path of the selected file
        private readonly List<string> _detectedLibraries = new(); // Store detected libraries
        private readonly List<string> _systemDependencies = new(); // Store system dependencies like ImageMagick
        private List<Library> _currentLibraries = new(); // Add this field
        private bool _isDarkMode = false;

        // Expanded list of Python built-in modules
        private static readonly HashSet<string> BuiltInPythonModules = new()
        {
            "argparse", "json", "logging", "os", "subprocess", "threading", "time", "tkinter",
            "math", "re", "platform", "tempfile", "sys", "random", "datetime", "shutil", "pathlib",
            "abc", "array", "ast", "asyncio", "base64", "bisect", "calendar", "cmd", "code",
            "codecs", "codeop", "collections", "configparser", "contextlib", "copy", "copyreg",
            "decimal", "difflib", "dis", "email", "enum", "fileinput", "fnmatch", "fractions",
            "functools", "glob", "hashlib", "heapq", "html", "http", "imaplib", "imp", "importlib",
            "inspect", "io", "ipaddress", "itertools", "linecache", "locale", "mimetypes", "numbers",
            "operator", "optparse", "os.path", "pdb", "pickle", "pkgutil", "pprint", "pwd", "queue",
            "select", "selectors", "shelve", "signal", "socket", "sqlite3", "ssl", "stat", "string",
            "struct", "textwrap", "timeit", "trace", "traceback", "types", "typing", "uuid", "warnings",
            "weakref", "xml", "zipfile", "zlib", "concurrent", "concurrent.futures", "docx"
        };
        private static readonly Dictionary<string, string> LibraryAliases = new()
        {
            { "cv2", "opencv-python" },
            { "PIL", "Pillow" },
            { "np", "numpy" },
            { "plt", "matplotlib" },
            { "pd", "pandas" },
            { "sklearn", "scikit-learn" },
            { "tensorflow", "tensorflow" },
            { "torch", "torch" },
            { "tf", "tensorflow" },
            { "keras", "keras" },
            { "seaborn", "seaborn" },
            { "sns", "seaborn" },
            { "scipy", "scipy" },
            { "sp", "scipy" },
            { "bs4", "beautifulsoup4" },
            { "requests", "requests" },
            { "rq", "requests" },
            { "flask", "flask" },
            { "django", "django" },
            { "sqlalchemy", "sqlalchemy" },
            { "sa", "sqlalchemy" },
            { "pytest", "pytest" },
            { "pandas", "pandas" },
            { "numpy", "numpy" },
            { "matplotlib", "matplotlib" },
            { "opencv-python", "opencv-python" },
            { "moviepy", "moviepy" },
            { "mediapipe", "mediapipe" },
            { "pydub", "pydub" },
            { "spleeter", "spleeter" },
            { "direct", "panda3d" },
            { "panda3d", "panda3d" },
            { "showbase", "panda3d" },
            { "direct.showbase", "panda3d" },
            { "direct.showbase.ShowBase", "panda3d" }
        };
        // Libraries that require ImageMagick
        private static readonly HashSet<string> LibrariesRequiringImageMagick = new()
        {
            "moviepy", "pydub"
        };

        // Libraries that should be ignored or replaced with alternatives
        private static readonly Dictionary<string, string> LibraryReplacements = new()
        {
            { "docx", "python-docx" }  // Use python-docx instead of docx
        };

        public MainWindow()
        {
            try
            {
                Debug.WriteLine("MainWindow constructor started.");
                InitializeComponent();
                
                // Initialize theme
                try
                {
                    var lightTheme = new ResourceDictionary
                    {
                        Source = new Uri("Themes/LightTheme.xaml", UriKind.Relative)
                    };
                    Resources.MergedDictionaries.Add(lightTheme);
                }
                catch (Exception ex)
                {
                    Debug.WriteLine($"Error loading light theme: {ex.Message}");
                    // Fallback to default colors if theme loading fails
                    Resources.MergedDictionaries.Add(new ResourceDictionary
                    {
                        ["BackgroundBrush"] = new SolidColorBrush(Colors.White),
                        ["ForegroundBrush"] = new SolidColorBrush(Colors.Black),
                        ["BorderBrush"] = new SolidColorBrush(Colors.Gray),
                        ["ButtonBackground"] = new SolidColorBrush(Colors.Blue),
                        ["ButtonHoverBackground"] = new SolidColorBrush(Colors.DarkBlue),
                        ["ButtonDisabledBackground"] = new SolidColorBrush(Colors.Gray),
                        ["ListViewBackground"] = new SolidColorBrush(Colors.White),
                        ["ListViewBorder"] = new SolidColorBrush(Colors.LightGray),
                        ["StatusBarBackground"] = new SolidColorBrush(Colors.LightGray)
                    });
                }
                
                _httpClient.DefaultRequestHeaders.AcceptEncoding.Add(new StringWithQualityHeaderValue("gzip"));
                LanguageComboBox.SelectedIndex = 0; // Default to C#
                
                // Set version information
                VersionText.Text = $"v{Assembly.GetExecutingAssembly().GetName().Version?.ToString(3) ?? "1.0.0"}";
                
                // Initialize LibraryListView with empty collection
                if (LibraryListView != null)
                {
                    LibraryListView.ItemsSource = _currentLibraries;
                }
                
                Debug.WriteLine("MainWindow initialized successfully.");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error in MainWindow constructor: {ex.Message}\nStack Trace: {ex.StackTrace}");
                MessageBox.Show($"Failed to initialize the app: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                Close();
            }
        }

        private void LanguageComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            try
            {
                Debug.WriteLine("LanguageComboBox_SelectionChanged started.");
                var selectedLanguage = ((ComboBoxItem)LanguageComboBox.SelectedItem)?.Content.ToString();
                _selectedLanguage = selectedLanguage;
                Debug.WriteLine($"LanguageComboBox changed to: {selectedLanguage}");
                ProjectTypeComboBox.Items.Clear();

                if (selectedLanguage == "C#")
                {
                    ProjectTypeComboBox.Items.Add(new ComboBoxItem { Content = "ASP.NET Core Web API" });
                    ProjectTypeComboBox.Items.Add(new ComboBoxItem { Content = "WPF Desktop App" });
                    ProjectTypeComboBox.Items.Add(new ComboBoxItem { Content = "Console Application" });
                }
                else if (selectedLanguage == "Python")
                {
                    ProjectTypeComboBox.Items.Add(new ComboBoxItem { Content = "Flask Web App" });
                    ProjectTypeComboBox.Items.Add(new ComboBoxItem { Content = "Tkinter GUI App" });
                    ProjectTypeComboBox.Items.Add(new ComboBoxItem { Content = "Script/CLI Tool" });
                }

                ProjectTypeComboBox.SelectedIndex = -1;
                LoadButton.IsEnabled = false;
                ProjectTypeComboBox.UpdateLayout(); // Force UI refresh
                Debug.WriteLine("LanguageComboBox_SelectionChanged completed.");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error in LanguageComboBox_SelectionChanged: {ex.Message}\nStack Trace: {ex.StackTrace}");
                MessageBox.Show($"Error updating language selection: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void ProjectTypeComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            try
            {
                Debug.WriteLine("ProjectTypeComboBox_SelectionChanged started.");
                LoadButton.IsEnabled = ProjectTypeComboBox.SelectedItem != null;
                Debug.WriteLine($"ProjectTypeComboBox changed. LoadButton.IsEnabled: {LoadButton.IsEnabled}");
                LoadButton.UpdateLayout(); // Force UI refresh
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error in ProjectTypeComboBox_SelectionChanged: {ex.Message}\nStack Trace: {ex.StackTrace}");
                MessageBox.Show($"Error updating project type selection: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void BrowseButton_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                Debug.WriteLine("BrowseButton_Click started.");
                var dialog = new OpenFileDialog
                {
                    Title = "Select a project file (e.g., .csproj or .py)",
                    Filter = "Project Files (*.csproj;*.py)|*.csproj;*.py|All Files (*.*)|*.*",
                    Multiselect = false
                };

                if (dialog.ShowDialog() == true)
                {
                    _selectedFilePath = dialog.FileName;
                    _selectedFolderPath = Path.GetDirectoryName(dialog.FileName);
                    if (string.IsNullOrEmpty(_selectedFolderPath))
                    {
                        Debug.WriteLine("Failed to extract folder path from the selected file.");
                        MessageBox.Show("Failed to extract folder path from the selected file.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                        return;
                    }
                    Debug.WriteLine($"Selected folder path: {_selectedFolderPath}");
                    Debug.WriteLine($"Selected file path: {_selectedFilePath}");
                    SelectedFolderText.Text = _selectedFolderPath;
                    AutoDetectProjectTypeAsync();
                }
                Debug.WriteLine("BrowseButton_Click completed.");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error in BrowseButton_Click: {ex.Message}\nStack Trace: {ex.StackTrace}");
                MessageBox.Show($"Error selecting file: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async void AutoDetectProjectTypeAsync()
        {
            if (string.IsNullOrEmpty(_selectedFolderPath) || string.IsNullOrEmpty(_selectedFilePath))
            {
                Debug.WriteLine("No folder path or file path selected.");
                await Dispatcher.InvokeAsync(() =>
                {
                    MessageBox.Show("Please select a file first.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                });
                return;
            }

            try
            {
                Debug.WriteLine("Starting auto-detection...");
                string? detectedLanguage = null;
                string? detectedProjectType = null;
                
                // Clear all dependency lists
                _detectedLibraries.Clear();
                _systemDependencies.Clear();
                _currentLibraries.Clear();
                LibraryListView.ItemsSource = null;
                LibraryListView.ItemsSource = _currentLibraries;

                string fileExtension = Path.GetExtension(_selectedFilePath).ToLower();
                Debug.WriteLine($"File extension: {fileExtension}");

                if (fileExtension == ".py")
                {
                    detectedLanguage = "Python";
                    Debug.WriteLine("Detected Python file");

                    // Check for requirements.txt
                    var requirementsFile = Path.Combine(_selectedFolderPath, "requirements.txt");
                    if (File.Exists(requirementsFile))
                    {
                        Debug.WriteLine($"Found requirements.txt: {requirementsFile}");
                        var lines = File.ReadAllLines(requirementsFile);
                        foreach (var line in lines)
                        {
                            var trimmedLine = line.Trim();
                            if (!string.IsNullOrEmpty(trimmedLine) && !trimmedLine.StartsWith("#"))
                            {
                                var libraryName = Regex.Match(trimmedLine, @"^([a-zA-Z0-9_-]+)").Value;
                                if (!string.IsNullOrEmpty(libraryName))
                                {
                                    string resolvedName = LibraryAliases.ContainsKey(libraryName) ? LibraryAliases[libraryName] : libraryName;
                                    if (!BuiltInPythonModules.Contains(resolvedName) && !_detectedLibraries.Contains(resolvedName))
                                    {
                                        _detectedLibraries.Add(resolvedName);
                                        Debug.WriteLine($"Detected library from requirements.txt: {resolvedName}");
                                    }
                                }
                            }
                        }
                    }

                    // Always scan the Python file content
                    Debug.WriteLine($"Scanning Python file: {_selectedFilePath}");
                    var content = File.ReadAllText(_selectedFilePath);
                    var contentLower = content.ToLower();

                    // Detect project type from imports and content
                    if (contentLower.Contains("flask") || contentLower.Contains("@app.route"))
                    {
                        detectedProjectType = "Flask Web App";
                        Debug.WriteLine("Detected Flask Web App");
                    }
                    else if (contentLower.Contains("tkinter") || contentLower.Contains("tk.") || contentLower.Contains("from tk "))
                    {
                        detectedProjectType = "Tkinter GUI App";
                        Debug.WriteLine("Detected Tkinter GUI App");
                    }
                    else
                    {
                        detectedProjectType = "Script/CLI Tool";
                        Debug.WriteLine("Detected Script/CLI Tool");
                    }

                    // Scan for imports with improved patterns
                    var importPatterns = new[]
                    {
                        @"^(?:import\s+([a-zA-Z0-9_.]+)(?:\s+as\s+[a-zA-Z0-9_]+)?)",  // import x, import x.y
                        @"^(?:from\s+([a-zA-Z0-9_.]+)\s+import\s+[a-zA-Z0-9_.*]+(?:\s+as\s+[a-zA-Z0-9_]+)?)",  // from x import y, from x.y import z
                        @"^(?:from\s+([a-zA-Z0-9_.]+)\s+import\s+\*)",  // from x import *
                        @"^(?:import\s+([a-zA-Z0-9_.]+)\s*,\s*[a-zA-Z0-9_.]+)",  // import x, y
                        @"^(?:from\s+([a-zA-Z0-9_.]+)\s+import\s+\([^)]+\))"  // from x import (y, z)
                    };

                    foreach (var pattern in importPatterns)
                    {
                        var regex = new Regex(pattern, RegexOptions.Multiline);
                        var matches = regex.Matches(content);
                        foreach (Match match in matches)
                        {
                            string libraryName = match.Groups[1].Value;
                            if (!string.IsNullOrEmpty(libraryName))
                            {
                                // Split by dots to handle module paths
                                var parts = libraryName.Split('.');
                                string baseLibrary = parts[0];
                                
                                // Check if this is a built-in module (including parent module)
                                if (BuiltInPythonModules.Contains(baseLibrary) || BuiltInPythonModules.Contains(libraryName))
                                {
                                    Debug.WriteLine($"Skipping built-in module: {libraryName}");
                                    continue;
                                }

                                // Check if we should use a replacement library
                                if (LibraryReplacements.ContainsKey(baseLibrary))
                                {
                                    baseLibrary = LibraryReplacements[baseLibrary];
                                    Debug.WriteLine($"Using replacement library: {baseLibrary} for {libraryName}");
                                }
                                
                                string resolvedName = LibraryAliases.ContainsKey(baseLibrary) ? LibraryAliases[baseLibrary] : 
                                                   LibraryAliases.ContainsKey(libraryName) ? LibraryAliases[libraryName] : baseLibrary;

                                if (!BuiltInPythonModules.Contains(resolvedName) && !_detectedLibraries.Contains(resolvedName))
                                {
                                    _detectedLibraries.Add(resolvedName);
                                    Debug.WriteLine($"Detected library from imports: {resolvedName} (original: {libraryName})");
                                    
                                    if (LibrariesRequiringImageMagick.Contains(resolvedName) && !_systemDependencies.Contains("ImageMagick"))
                                    {
                                        _systemDependencies.Add("ImageMagick");
                                        Debug.WriteLine("Detected system dependency: ImageMagick");
                                    }
                                }
                            }
                        }
                    }
                }
                else if (fileExtension == ".csproj")
                {
                    detectedLanguage = "C#";
                    Debug.WriteLine("Detected C# project");
                    
                    var csprojContent = File.ReadAllText(_selectedFilePath);
                    if (csprojContent.Contains("Microsoft.NET.Sdk.Web"))
                    {
                        detectedProjectType = "ASP.NET Core Web API";
                        Debug.WriteLine("Detected ASP.NET Core Web API");
                    }
                    else if (csprojContent.Contains("UseWPF"))
                    {
                        detectedProjectType = "WPF Desktop App";
                        Debug.WriteLine("Detected WPF Desktop App");
                    }
                    else
                    {
                        detectedProjectType = "Console Application";
                        Debug.WriteLine("Detected Console Application");
                    }

                    // Parse PackageReference elements from csproj
                    var packageRefPattern = @"<PackageReference\s+Include=""([^""]+)""\s+Version=""([^""]+)""\s*/?>";
                    var matches = Regex.Matches(csprojContent, packageRefPattern, RegexOptions.IgnoreCase);
                    foreach (Match match in matches)
                    {
                        var packageName = match.Groups[1].Value;
                        var version = match.Groups[2].Value;
                        if (!string.IsNullOrEmpty(packageName))
                        {
                            _detectedLibraries.Add(packageName);
                            Debug.WriteLine($"Detected NuGet package: {packageName} (Version: {version})");
                        }
                    }

                    // Also check for SDK references
                    var sdkRefPattern = @"<PackageReference\s+Include=""Microsoft\..*?Sdk[^""]*""\s+Version=""([^""]+)""\s*/?>";
                    matches = Regex.Matches(csprojContent, sdkRefPattern);
                    foreach (Match match in matches)
                    {
                        var sdkName = match.Groups[0].Value;
                        if (!string.IsNullOrEmpty(sdkName))
                        {
                            _detectedLibraries.Add(sdkName);
                            Debug.WriteLine($"Detected SDK reference: {sdkName}");
                        }
                    }

                    // Check for implicit SDK references based on UseWPF
                    if (csprojContent.Contains("<UseWPF>true</UseWPF>"))
                    {
                        _detectedLibraries.Add("Microsoft.WindowsDesktop.App.WPF");
                        Debug.WriteLine("Detected WPF SDK reference");
                    }
                }

                // Update UI on the UI thread
                await Dispatcher.InvokeAsync(() =>
                {
                    if (detectedLanguage != null)
                    {
                        Debug.WriteLine($"Setting detected language: {detectedLanguage}");
                        var languageItem = LanguageComboBox.Items.Cast<ComboBoxItem>()
                            .FirstOrDefault(item => item.Content.ToString() == detectedLanguage);
                        
                        if (languageItem != null)
                        {
                            LanguageComboBox.SelectedItem = languageItem;
                            LanguageComboBox.UpdateLayout();

                            if (detectedProjectType != null)
                            {
                                Debug.WriteLine($"Setting detected project type: {detectedProjectType}");
                                var projectTypeItem = ProjectTypeComboBox.Items.Cast<ComboBoxItem>()
                                    .FirstOrDefault(item => item.Content.ToString() == detectedProjectType);
                                
                                if (projectTypeItem != null)
                                {
                                    ProjectTypeComboBox.SelectedItem = projectTypeItem;
                                    ProjectTypeComboBox.UpdateLayout();
                                    LoadButton_Click(null, null);
                                }
                            }
                        }
                    }

                    string message = $"Detected Language: {detectedLanguage ?? "Unknown"}\n" +
                                   $"Project Type: {detectedProjectType ?? "Unknown"}\n" +
                                   $"Dependencies Found: {_detectedLibraries.Count}";
                    MessageBox.Show(message, "Detection Result", MessageBoxButton.OK, MessageBoxImage.Information);
                });
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error in AutoDetectProjectTypeAsync: {ex.Message}\nStack Trace: {ex.StackTrace}");
                await Dispatcher.InvokeAsync(() =>
                {
                    MessageBox.Show($"Error detecting project type: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                });
            }
        }

        private async void LoadButton_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                Debug.WriteLine("LoadButton_Click started.");
                LoadButton.IsEnabled = false;
                ScanProgressBar.Visibility = Visibility.Visible;
                LoadingText.Visibility = Visibility.Visible;
                StatusText.Text = "Loading dependencies...";

                // Clear only the display lists, not the detected libraries
                _systemDependencies.Clear();
                _currentLibraries.Clear();
                LibraryListView.ItemsSource = null;

                Debug.WriteLine($"Number of detected libraries: {_detectedLibraries.Count}");
                foreach (var lib in _detectedLibraries)
                {
                    Debug.WriteLine($"Detected library: {lib}");
                }

                if (_selectedLanguage == "Python" && 
                    ProjectTypeComboBox.SelectedItem is ComboBoxItem item && 
                    item.Content.ToString() == "Tkinter GUI App")
                {
                    await LoadPythonLibraries();
                    StatusText.Text = $"Libraries loaded successfully ({_detectedLibraries.Count} found)";
                    ExportButton.IsEnabled = true;
                }
                else if (_selectedLanguage == "C#")
                {
                    await LoadCSharpLibraries();
                    StatusText.Text = $"Libraries loaded successfully ({_detectedLibraries.Count} found)";
                    ExportButton.IsEnabled = true;
                }
                else
                {
                    // Handle other project types
                    StatusText.Text = "Project type not supported yet";
                }

                ScanProgressBar.Visibility = Visibility.Collapsed;
                LoadingText.Visibility = Visibility.Collapsed;
                LoadButton.IsEnabled = true;
                Debug.WriteLine("LoadButton_Click completed.");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error in LoadButton_Click: {ex.Message}\nStack Trace: {ex.StackTrace}");
                MessageBox.Show($"Error loading dependencies: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                LoadButton.IsEnabled = true;
                ScanProgressBar.Visibility = Visibility.Collapsed;
                LoadingText.Visibility = Visibility.Collapsed;
                StatusText.Text = "Error loading dependencies";
            }
        }

        private string CheckImageMagickInstallation()
        {
            try
            {
                Process process = new Process();
                process.StartInfo.FileName = "magick";
                process.StartInfo.Arguments = "--version";
                process.StartInfo.RedirectStandardOutput = true;
                process.StartInfo.UseShellExecute = false;
                process.StartInfo.CreateNoWindow = true;
                process.Start();
                string output = process.StandardOutput.ReadToEnd();
                process.WaitForExit();
                if (process.ExitCode == 0)
                {
                    var versionMatch = Regex.Match(output, @"Version: ImageMagick (\S+)");
                    return versionMatch.Success ? versionMatch.Groups[1].Value : "Installed";
                }
                return "Not installed";
            }
            catch
            {
                return "Not installed";
            }
        }

        private void CopyButton_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                Debug.WriteLine("CopyButton_Click started.");
                if (sender is Button button && button.Tag is Library library)
                {
                    string command = GenerateInstallCommand(library);
                    Clipboard.SetText(command);
                    MessageBox.Show($"Copied to clipboard: {command}", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                Debug.WriteLine("CopyButton_Click completed.");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error in CopyButton_Click: {ex.Message}\nStack Trace: {ex.StackTrace}");
                MessageBox.Show($"Failed to copy to clipboard: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private string GenerateInstallCommand(Library library)
        {
            if (library.Name == "ImageMagick")
            {
                return "# Install ImageMagick using your system package manager (e.g., 'apt install imagemagick' on Ubuntu)";
            }

            if (library.Version == "Built-in" || library.Version == "Error" || library.Version == "-")
            {
                return $"# {library.Name} is {library.Version.ToLower()} or unavailable";
            }

            if (_selectedLanguage == "C#")
            {
                return $"dotnet add package {library.Name} --version {library.Version}";
            }
            else if (_selectedLanguage == "Python")
            {
                return $"pip install {library.Name}=={library.Version}";
            }

            return "# Unknown language";
        }

        private async Task<List<Library>> GetRecommendationsAsync(string language, string projectType)
        {
            var libraries = new List<Library>();

            if (language == "C#")
            {
                switch (projectType)
                {
                    case "ASP.NET Core Web API":
                        libraries.Add(new Library { Name = "Swashbuckle.AspNetCore", Version = await GetNuGetVersionAsync("Swashbuckle.AspNetCore", "6.5.0"), Purpose = "Swagger/OpenAPI documentation", Description = "Swagger tools for documenting ASP.NET Core APIs" });
                        libraries.Add(new Library { Name = "MediatR", Version = await GetNuGetVersionAsync("MediatR", "12.0.1"), Purpose = "CQRS and mediator pattern", Description = "Simple mediator implementation in .NET" });
                        libraries.Add(new Library { Name = "Serilog.AspNetCore", Version = await GetNuGetVersionAsync("Serilog.AspNetCore", "8.0.0"), Purpose = "Structured logging", Description = "Structured logging for ASP.NET Core" });
                        break;
                    case "WPF Desktop App":
                        libraries.Add(new Library { Name = "MaterialDesignThemes", Version = await GetNuGetVersionAsync("MaterialDesignThemes", "4.9.0"), Purpose = "Modern UI styling", Description = "Material Design themes for WPF applications" });
                        libraries.Add(new Library { Name = "Prism.Core", Version = await GetNuGetVersionAsync("Prism.Core", "8.1.97"), Purpose = "MVVM framework", Description = "Prism is a framework for building loosely coupled, maintainable, and testable XAML applications" });
                        libraries.Add(new Library { Name = "Newtonsoft.Json", Version = await GetNuGetVersionAsync("Newtonsoft.Json", "13.0.3"), Purpose = "JSON serialization", Description = "Popular high-performance JSON framework for .NET" });
                        break;
                    case "Console Application":
                        libraries.Add(new Library { Name = "CommandLineParser", Version = await GetNuGetVersionAsync("CommandLineParser", "2.9.1"), Purpose = "CLI argument parsing", Description = "Command line parsing library for CLR applications" });
                        libraries.Add(new Library { Name = "NLog", Version = await GetNuGetVersionAsync("NLog", "5.2.8"), Purpose = "Logging framework", Description = "Flexible and high-performance logging framework" });
                        libraries.Add(new Library { Name = "System.Text.Json", Version = await GetNuGetVersionAsync("System.Text.Json", "8.0.0"), Purpose = "Built-in JSON handling", Description = "Built-in high-performance JSON framework" });
                        break;
                }
            }
            else if (language == "Python")
            {
                if (_detectedLibraries.Count > 0)
                {
                    foreach (var libraryName in _detectedLibraries)
                    {
                        string purpose = libraryName switch
                        {
                            "flask" => "Lightweight web framework",
                            "requests" => "HTTP requests",
                            "pandas" => "Data manipulation",
                            "numpy" => "Numerical computing",
                            "matplotlib" => "Data visualization",
                            "opencv-python" => "Computer vision",
                            "moviepy" => "Video editing",
                            "mediapipe" => "Media processing",
                            "scipy" => "Scientific computing",
                            "Pillow" => "Image processing",
                            "pydub" => "Audio processing",
                            "spleeter" => "Audio source separation",
                            "panda3d" => "3D game engine",
                            "pygame" => "Game development",
                            "keyboard" => "Keyboard control",
                            _ => "Used in project"
                        };

                        string initialDescription = libraryName switch
                        {
                            "flask" => "A lightweight WSGI web application framework",
                            "requests" => "HTTP library for Python",
                            "pandas" => "Data analysis and manipulation tool",
                            "numpy" => "Fundamental package for scientific computing",
                            "matplotlib" => "Comprehensive library for creating static, animated, and interactive visualizations",
                            "opencv-python" => "Computer vision and image processing library",
                            "moviepy" => "Video editing library for Python",
                            "mediapipe" => "Cross-platform, customizable ML solutions",
                            "scipy" => "Fundamental algorithms for scientific computing",
                            "Pillow" => "Python Imaging Library fork",
                            "pydub" => "Manipulate audio with a simple and easy interface",
                            "spleeter" => "Music source separation library",
                            "panda3d" => "3D game engine and rendering framework",
                            "pygame" => "Set of Python modules designed for writing video games",
                            "keyboard" => "Hook and simulate keyboard events on Windows and Linux",
                            _ => "Loading description..."
                        };

                        string version = await GetPyPiVersionAsync(libraryName, "Not found");

                        libraries.Add(new Library
                        {
                            Name = libraryName,
                            Version = version,
                            Purpose = purpose,
                            Description = initialDescription
                        });
                    }
                }
                else
                {
                    libraries.Add(new Library { Name = "None", Version = "-", Purpose = "No external dependencies detected in the code", Description = "No dependencies to describe" });
                }
            }

            if (libraries.Count == 0)
            {
                libraries.Add(new Library { Name = "None", Version = "-", Purpose = "No external dependencies detected; only built-in modules used", Description = "No dependencies to describe" });
            }

            return libraries;
        }

        private async Task<string> GetNuGetVersionAsync(string packageName, string fallbackVersion)
        {
            try
            {
                Debug.WriteLine($"Fetching NuGet version for {packageName}...");
                var url = $"https://api-v2v3search-0.nuget.org/query?q={packageName.ToLower()}&prerelease=false&take=1";
                var response = await _httpClient.GetFromJsonAsync<NuGetSearchResponse>(url);
                var package = response?.Data?.FirstOrDefault();
                string version = package?.Version ?? fallbackVersion;
                if (version == fallbackVersion)
                {
                    Debug.WriteLine($"NuGet Search API returned no data for {packageName}. Using fallback version.");
                    MessageBox.Show($"NuGet Search API returned no data for {packageName}. Using fallback version.", "Warning", MessageBoxButton.OK, MessageBoxImage.Warning);
                }
                else
                {
                    Debug.WriteLine($"NuGet version for {packageName}: {version}");
                }
                return version;
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine($"NuGet Search API failed for {packageName}: {ex.Message}");
                MessageBox.Show($"NuGet Search API failed for {packageName}: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                return fallbackVersion;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Unexpected error fetching NuGet version for {packageName}: {ex.Message}\nStack Trace: {ex.StackTrace}");
                MessageBox.Show($"Unexpected error fetching NuGet version for {packageName}: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                return fallbackVersion;
            }
        }

        private async Task<string> GetPyPiVersionAsync(string packageName, string fallbackVersion)
        {
            try
            {
                Debug.WriteLine($"Fetching PyPI version for {packageName}...");
                
                // Normalize package name (remove any spaces and convert to lowercase)
                packageName = packageName.Trim().ToLower();
                
                // Handle common package name variations
                if (LibraryAliases.ContainsKey(packageName))
                {
                    packageName = LibraryAliases[packageName];
                    Debug.WriteLine($"Resolved alias to: {packageName}");
                }

                // Skip built-in modules
                if (BuiltInPythonModules.Contains(packageName))
                {
                    Debug.WriteLine($"{packageName} is a built-in module");
                    return "Built-in";
                }

                var url = $"https://pypi.org/pypi/{packageName}/json";
                Debug.WriteLine($"Requesting URL: {url}");

                var response = await _httpClient.GetFromJsonAsync<PyPiResponse>(url);
                
                if (response?.Info?.Version == null)
                {
                    Debug.WriteLine($"No version found for {packageName}");
                    if (!BuiltInPythonModules.Contains(packageName) && !LibraryAliases.ContainsValue(packageName))
                    {
                        MessageBox.Show($"No version information found for {packageName}. The package might not exist on PyPI.", 
                            "Warning", MessageBoxButton.OK, MessageBoxImage.Warning);
                    }
                    return fallbackVersion;
                }

                // Update the library description in the current libraries list
                var library = _currentLibraries.FirstOrDefault(l => l.Name.Equals(packageName, StringComparison.OrdinalIgnoreCase));
                if (library != null)
                {
                    library.Description = response.Info.Summary ?? response.Info.Description ?? "No description available.";
                }

                Debug.WriteLine($"Successfully fetched version {response.Info.Version} for {packageName}");
                return response.Info.Version;
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine($"HTTP request failed for {packageName}: {ex.Message}");
                Debug.WriteLine($"Status code: {ex.StatusCode}");
                if (!BuiltInPythonModules.Contains(packageName) && !LibraryAliases.ContainsValue(packageName))
                {
                    MessageBox.Show($"Failed to fetch version for {packageName}: {ex.Message}", 
                        "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
                return fallbackVersion;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Unexpected error fetching PyPI version for {packageName}: {ex.Message}");
                Debug.WriteLine($"Stack Trace: {ex.StackTrace}");
                if (!BuiltInPythonModules.Contains(packageName) && !LibraryAliases.ContainsValue(packageName))
                {
                    MessageBox.Show($"Unexpected error fetching version for {packageName}: {ex.Message}", 
                        "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
                return fallbackVersion;
            }
        }

        private void ExportButton_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                Debug.WriteLine("ExportButton_Click started.");
                var saveFileDialog = new SaveFileDialog
                {
                    Filter = "Text files (*.txt)|*.txt|All files (*.*)|*.*",
                    Title = "Export Dependencies",
                    DefaultExt = "txt"
                };

                if (saveFileDialog.ShowDialog() == true)
                {
                    var libraries = LibraryListView.ItemsSource as List<Library>;
                    if (libraries != null)
                    {
                        var lines = new List<string>();
                        lines.Add($"Dependency Export - {DateTime.Now}");
                        lines.Add($"Language: {_selectedLanguage}");
                        lines.Add($"Project Type: {((ComboBoxItem)ProjectTypeComboBox.SelectedItem)?.Content}");
                        lines.Add($"Project Path: {_selectedFolderPath}");
                        lines.Add("");
                        lines.Add("Dependencies:");
                        lines.Add("");

                        foreach (var library in libraries)
                        {
                            lines.Add($"Name: {library.Name}");
                            lines.Add($"Version: {library.Version}");
                            lines.Add($"Required Version: {library.RequiredVersion}");
                            lines.Add($"Purpose: {library.Purpose}");
                            lines.Add($"Description: {library.Description}");
                            lines.Add($"Install Command: {GenerateInstallCommand(library)}");
                            lines.Add("");
                        }

                        File.WriteAllLines(saveFileDialog.FileName, lines);
                        MessageBox.Show("Dependencies exported successfully!", "Success", MessageBoxButton.OK, MessageBoxImage.Information);
                    }
                }
                Debug.WriteLine("ExportButton_Click completed.");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Error in ExportButton_Click: {ex.Message}\nStack Trace: {ex.StackTrace}");
                MessageBox.Show($"Error exporting dependencies: {ex.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void ExitMenuItem_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void CopyMenuItem_Click(object sender, RoutedEventArgs e)
        {
            if (LibraryListView?.SelectedItem is Library selectedLibrary)
            {
                Clipboard.SetText(GenerateInstallCommand(selectedLibrary));
                StatusText.Text = "Copied to clipboard";
            }
        }

        private void SelectAllMenuItem_Click(object sender, RoutedEventArgs e)
        {
            if (LibraryListView != null)
            {
                LibraryListView.SelectAll();
            }
        }

        private void ToggleDarkMode_Click(object sender, RoutedEventArgs e)
        {
            if (sender is MenuItem menuItem)
            {
                _isDarkMode = !_isDarkMode;
                menuItem.IsChecked = _isDarkMode;
                
                try
                {
                    // Clear existing merged dictionaries
                    Resources.MergedDictionaries.Clear();
                    
                    // Add the selected theme
                    var themeDict = new ResourceDictionary
                    {
                        Source = new Uri(_isDarkMode ? "Themes/DarkTheme.xaml" : "Themes/LightTheme.xaml", UriKind.Relative)
                    };
                    Resources.MergedDictionaries.Add(themeDict);
                    
                    StatusText.Text = _isDarkMode ? "Dark mode enabled" : "Dark mode disabled";
                }
                catch (Exception ex)
                {
                    Debug.WriteLine($"Error switching theme: {ex.Message}");
                    StatusText.Text = "Error switching theme";
                }
            }
        }

        private void AboutMenuItem_Click(object sender, RoutedEventArgs e)
        {
            var version = Assembly.GetExecutingAssembly().GetName().Version?.ToString(3) ?? "1.0.0";
            MessageBox.Show(
                $"Dependency Finder\nVersion {version}\n\nA tool to help identify and manage project dependencies.",
                "About Dependency Finder",
                MessageBoxButton.OK,
                MessageBoxImage.Information
            );
        }

        private void SearchTextBox_TextChanged(object sender, TextChangedEventArgs e)
        {
            if (LibraryListView == null) return;

            if (string.IsNullOrWhiteSpace(SearchTextBox.Text) || SearchTextBox.Text == "Search libraries...")
            {
                LibraryListView.ItemsSource = _currentLibraries;
                return;
            }

            var searchText = SearchTextBox.Text.ToLower();
            var filteredLibraries = _currentLibraries.Where(lib =>
                lib.Name.ToLower().Contains(searchText) ||
                (lib.Description?.ToLower().Contains(searchText) ?? false) ||
                lib.Purpose.ToLower().Contains(searchText)
            ).ToList();

            LibraryListView.ItemsSource = filteredLibraries;
        }

        private void SearchTextBox_GotFocus(object sender, RoutedEventArgs e)
        {
            if (SearchTextBox.Text == "Search libraries...")
            {
                SearchTextBox.Text = "";
            }
        }

        private void SearchTextBox_LostFocus(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(SearchTextBox.Text))
            {
                SearchTextBox.Text = "Search libraries...";
            }
        }

        private async Task LoadPythonLibraries()
        {
            _currentLibraries.Clear();

            // Only add libraries that were actually detected in the project
            if (_detectedLibraries.Count > 0)
            {
                foreach (var libraryName in _detectedLibraries)
                {
                    string purpose = libraryName switch
                    {
                        "flask" => "Lightweight web framework",
                        "requests" => "HTTP requests",
                        "pandas" => "Data manipulation",
                        "numpy" => "Numerical computing",
                        "matplotlib" => "Data visualization",
                        "opencv-python" => "Computer vision",
                        "moviepy" => "Video editing",
                        "mediapipe" => "Media processing",
                        "scipy" => "Scientific computing",
                        "Pillow" => "Image processing",
                        "pydub" => "Audio processing",
                        "spleeter" => "Audio source separation",
                        "panda3d" => "3D game engine",
                        "pygame" => "Game development",
                        "keyboard" => "Keyboard control",
                        "reportlab" => "PDF generation",
                        "pdfplumber" => "PDF text extraction",
                        "nltk" => "Natural language processing",
                        "textblob" => "Text processing",
                        "python-docx" => "Word document processing",
                        "ebooklib" => "Ebook file handling",
                        "pyinstaller" => "Application packaging",
                        _ => "Used in project"
                    };

                    string initialDescription = libraryName switch
                    {
                        "flask" => "A lightweight WSGI web application framework",
                        "requests" => "HTTP library for Python",
                        "pandas" => "Data analysis and manipulation tool",
                        "numpy" => "Fundamental package for scientific computing",
                        "matplotlib" => "Comprehensive library for creating static, animated, and interactive visualizations",
                        "opencv-python" => "Computer vision and image processing library",
                        "moviepy" => "Video editing library for Python",
                        "mediapipe" => "Cross-platform, customizable ML solutions",
                        "scipy" => "Fundamental algorithms for scientific computing",
                        "Pillow" => "Python Imaging Library fork",
                        "pydub" => "Manipulate audio with a simple and easy interface",
                        "spleeter" => "Music source separation library",
                        "panda3d" => "3D game engine and rendering framework",
                        "pygame" => "Set of Python modules designed for writing video games",
                        "keyboard" => "Hook and simulate keyboard events on Windows and Linux",
                        "reportlab" => "Library for creating PDF documents in Python",
                        "pdfplumber" => "Plumb PDFs for detailed information about text, lines, and rectangles",
                        "nltk" => "Natural Language Toolkit for text processing and analysis",
                        "textblob" => "Simplified text processing for sentiment analysis and more",
                        "python-docx" => "Python library for creating and updating Microsoft Word (.docx) files",
                        "ebooklib" => "Python E-book library for handling EPUB2/EPUB3 files",
                        "pyinstaller" => "Converts Python programs into stand-alone executables",
                        _ => "Loading description..."
                    };

                    try
                    {
                        // Create initial library entry
                        var library = new Library
                        {
                            Name = libraryName,
                            Version = "Loading...",
                            Purpose = purpose,
                            Description = initialDescription,
                            ActionText = "Copy"
                        };
                        _currentLibraries.Add(library);

                        // Update UI immediately with initial data
                        LibraryListView.ItemsSource = null;
                        LibraryListView.ItemsSource = _currentLibraries;

                        // Fetch PyPI data
                        var url = $"https://pypi.org/pypi/{libraryName}/json";
                        var response = await _httpClient.GetFromJsonAsync<PyPiResponse>(url);
                        
                        if (response?.Info != null)
                        {
                            // Update version
                            library.Version = response.Info.Version ?? "Not found";
                            
                            // Update description if available
                            if (!string.IsNullOrWhiteSpace(response.Info.Summary))
                            {
                                library.Description = response.Info.Summary;
                            }
                            else if (!string.IsNullOrWhiteSpace(response.Info.Description))
                            {
                                library.Description = response.Info.Description;
                            }

                            // Refresh UI after each update
                            LibraryListView.ItemsSource = null;
                            LibraryListView.ItemsSource = _currentLibraries;
                        }
                    }
                    catch (Exception ex)
                    {
                        Debug.WriteLine($"Error loading data for {libraryName}: {ex.Message}");
                        // Keep the initial data if there's an error
                    }
                }
            }
            else
            {
                // If no libraries were detected, show a message
                _currentLibraries.Add(new Library
                {
                    Name = "No dependencies",
                    Version = "-",
                    Purpose = "No external dependencies detected",
                    Description = "Only built-in Python modules are used in this project",
                    ActionText = "Copy"
                });
            }

            // Final UI refresh
            LibraryListView.ItemsSource = null;
            LibraryListView.ItemsSource = _currentLibraries;
        }

        private async Task LoadCSharpLibraries()
        {
            _currentLibraries.Clear();

            if (_detectedLibraries.Count > 0)
            {
                foreach (var libraryName in _detectedLibraries)
                {
                    string purpose = libraryName switch
                    {
                        var n when n.StartsWith("Microsoft.AspNetCore") => "ASP.NET Core framework",
                        var n when n.StartsWith("Microsoft.EntityFrameworkCore") => "Entity Framework Core ORM",
                        var n when n.StartsWith("Microsoft.Extensions") => ".NET Extensions",
                        "Newtonsoft.Json" => "JSON framework",
                        "System.Text.Json" => "Built-in JSON handling",
                        "Serilog" => "Structured logging",
                        "NLog" => "Flexible logging",
                        "log4net" => "Logging framework",
                        "AutoMapper" => "Object-object mapping",
                        "FluentValidation" => "Object validation",
                        "MediatR" => "Mediator pattern implementation",
                        "Dapper" => "Micro-ORM",
                        "Swashbuckle.AspNetCore" => "Swagger/OpenAPI tools",
                        "Microsoft.NET.Test.Sdk" => "Testing framework",
                        "xunit" => "Unit testing framework",
                        "NUnit" => "Unit testing framework",
                        "Moq" => "Mocking framework",
                        "MaterialDesignThemes" => "Material Design UI",
                        "Prism.Core" => "MVVM framework",
                        "CommunityToolkit.Mvvm" => "MVVM toolkit",
                        _ => "Project dependency"
                    };

                    string initialDescription = libraryName switch
                    {
                        var n when n.StartsWith("Microsoft.AspNetCore") => "Core framework for building web apps with ASP.NET Core",
                        var n when n.StartsWith("Microsoft.EntityFrameworkCore") => "Modern object-database mapper for .NET",
                        var n when n.StartsWith("Microsoft.Extensions") => "Core .NET extension libraries",
                        "Newtonsoft.Json" => "Popular high-performance JSON framework for .NET",
                        "System.Text.Json" => "Built-in high-performance JSON library",
                        "Serilog" => "Structured logging for modern applications",
                        "NLog" => "Flexible and high-performance logging framework",
                        "log4net" => "Highly configurable logging framework",
                        "AutoMapper" => "Convention-based object-object mapper",
                        "FluentValidation" => "Library for building strongly-typed validation rules",
                        "MediatR" => "Simple mediator implementation in .NET",
                        "Dapper" => "Simple object mapper for .NET",
                        "Swashbuckle.AspNetCore" => "Swagger tools for documenting ASP.NET Core APIs",
                        "Microsoft.NET.Test.Sdk" => ".NET testing infrastructure",
                        "xunit" => "Free, open source, community-focused unit testing tool",
                        "NUnit" => "Unit-testing framework for all .NET languages",
                        "Moq" => "Mocking framework for .NET",
                        "MaterialDesignThemes" => "Material Design themes for WPF",
                        "Prism.Core" => "Framework for building loosely coupled applications",
                        "CommunityToolkit.Mvvm" => "Modern, fast, and modular MVVM library",
                        _ => "Loading description..."
                    };

                    try
                    {
                        // Create initial library entry
                        var library = new Library
                        {
                            Name = libraryName,
                            Version = "Loading...",
                            Purpose = purpose,
                            Description = initialDescription,
                            ActionText = "Copy"
                        };
                        _currentLibraries.Add(library);

                        // Update UI immediately with initial data
                        LibraryListView.ItemsSource = null;
                        LibraryListView.ItemsSource = _currentLibraries;

                        // Fetch NuGet data
                        var url = $"https://api-v2v3search-0.nuget.org/query?q={Uri.EscapeDataString(libraryName)}&prerelease=false&take=1";
                        var response = await _httpClient.GetFromJsonAsync<NuGetSearchResponse>(url);
                        
                        if (response?.Data?.FirstOrDefault()?.Version != null)
                        {
                            library.Version = response.Data[0].Version;
                        }

                        // Refresh UI after each update
                        LibraryListView.ItemsSource = null;
                        LibraryListView.ItemsSource = _currentLibraries;
                    }
                    catch (Exception ex)
                    {
                        Debug.WriteLine($"Error loading data for {libraryName}: {ex.Message}");
                        // Keep the initial data if there's an error
                    }
                }
            }
            else
            {
                _currentLibraries.Add(new Library
                {
                    Name = "No dependencies",
                    Version = "-",
                    Purpose = "No external dependencies detected",
                    Description = "Only built-in .NET libraries are used in this project",
                    ActionText = "Copy"
                });
            }

            // Final UI refresh
            LibraryListView.ItemsSource = null;
            LibraryListView.ItemsSource = _currentLibraries;
        }
    }

    public class NuGetSearchResponse
    {
        public List<NuGetSearchItem>? Data { get; set; }
    }

    public class NuGetSearchItem
    {
        public string? Version { get; set; }
    }

    public class PyPiResponse
    {
        public PyPiInfo? Info { get; set; }
    }

    public class PyPiInfo
    {
        public string? Version { get; set; }
        public string? Summary { get; set; }
        public string? Description { get; set; }
    }
}