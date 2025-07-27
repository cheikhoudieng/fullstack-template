module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:import/errors',
    'plugin:react/recommended',
    'plugin:jsx-a11y/recommended',
  ],
  plugins: ['react', 'import', 'jsx-a11y', 'unicorn'],
  rules: {
    'react/prop-types': 0,
    'linebreak-style': 1,
    'unicorn/prefer-includes': 'warn',
    'unicorn/prefer-dom-node-remove': 'warn',
    'unicorn/prefer-dom-node-append': 'warn',
    'no-cond-assign': 'warn',
    'no-empty': 'warn',
    'no-undef': 'warn',
  },
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true,
    },
  },
  env: {
    es6: true,
    browser: true,
    node: true,
  },
  settings: {
    react: {
      version: 'detect',
    },
  },
};
