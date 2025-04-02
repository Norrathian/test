using System.Windows.Media;

namespace dependencyfinder
{
    public class Library
    {
        public string Name { get; set; } = string.Empty;
        public string Version { get; set; } = string.Empty;
        public string RequiredVersion { get; set; } = "-";
        public Brush VersionStatusColor { get; set; } = Brushes.Black;
        public string Purpose { get; set; } = string.Empty;
        public string Description { get; set; } = "No description available.";
        public string ActionText { get; set; } = "Copy";
        public Brush ActionColor { get; set; } = Brushes.Black;
        public string DownloadUrl { get; set; } = string.Empty;
    }
}