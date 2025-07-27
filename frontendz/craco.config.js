const path = require('path');

module.exports = {
  webpack: {
    alias: {
      // Évite le problème du "double React" avec npm link
      react: path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
    },
  },

  jest: {
    configure: {
      moduleNameMapper: {
        '^react$': '<rootDir>/node_modules/react',
        '^react-dom$': '<rootDir>/node_modules/react-dom',
      },
    },
  },
};
