using System.Windows;
using System.Diagnostics;

namespace dependencyfinder
{
    public partial class App : Application
    {
        public App()
        {
            DispatcherUnhandledException += App_DispatcherUnhandledException;
        }

        private void App_DispatcherUnhandledException(object sender, System.Windows.Threading.DispatcherUnhandledExceptionEventArgs e)
        {
            Debug.WriteLine($"Unhandled exception: {e.Exception.Message}\nStack Trace: {e.Exception.StackTrace}");
            MessageBox.Show($"An unexpected error occurred: {e.Exception.Message}", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
            e.Handled = true; // Prevent the app from crashing
        }
    }
}