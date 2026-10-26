import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled UI Error caught by ErrorBoundary:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 max-w-2xl mx-auto my-12 bg-white rounded-3xl shadow-2xl border border-rose-200 space-y-4">
          <div className="flex items-center space-x-3 text-rose-600">
            <AlertTriangle className="h-8 w-8" />
            <div>
              <h2 className="text-xl font-extrabold text-teal-950">Application Render Error</h2>
              <p className="text-xs text-teal-700 font-mono">React Error Boundary Caught an Exception</p>
            </div>
          </div>

          <div className="p-4 bg-rose-50 rounded-2xl border border-rose-200 text-xs font-mono text-rose-900 overflow-x-auto whitespace-pre-wrap">
            {this.state.error?.toString()}
          </div>

          {this.state.errorInfo && (
            <details className="text-[11px] text-teal-800 bg-teal-50 p-3 rounded-xl border border-teal-800/20">
              <summary className="font-bold cursor-pointer mb-2">Component Stack Trace</summary>
              <pre className="font-mono overflow-x-auto whitespace-pre-wrap text-[10px]">
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}

          <div className="pt-2 flex justify-end">
            <button
              onClick={this.handleReset}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-teal-900 hover:bg-teal-850 text-white font-bold text-xs uppercase shadow-tactile transition"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Reload Application</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

