# Dependency Finder

A WPF application that helps developers analyze and manage project dependencies for both Python and C# projects.

## Features

- **Multi-Language Support**: Analyzes both Python and C# projects
- **Automatic Detection**: Automatically detects project type and dependencies
- **Real-Time Updates**: Fetches latest version information from PyPI and NuGet
- **Detailed Information**: Shows purpose and description for common libraries
- **Export Functionality**: Export dependency information to various formats
- **Search**: Filter dependencies by name, purpose, or description
- **Dark Mode**: Supports both light and dark themes

## Supported Project Types

### Python
- Flask Web Apps
- Tkinter GUI Apps
- Script/CLI Tools

### C#
- ASP.NET Core Web API
- WPF Desktop Apps
- Console Applications

## Dependencies

- .NET 8.0
- WPF Framework
- System.Net.Http.Json (8.0.0)
- Microsoft.Win32.SystemEvents (8.0.0)

## Installation

1. Clone the repository
2. Open the solution in Visual Studio 2022
3. Build and run the project

## Usage

1. Select your project language (Python/C#)
2. Choose the project type
3. Browse and select your project file
4. Click "Load Recommendations" to analyze dependencies
5. Use the search box to filter results
6. Click "Copy" next to any dependency to copy its installation command
7. Export the full dependency list if needed

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/) 