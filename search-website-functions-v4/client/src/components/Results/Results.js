import React from 'react';
import Result from './Result/Result';

import "./Results.css";

export default function Results(props) {

  let results = props.documents.map((result, index) => {
    return <Result 
        key={index} 
        document={result.document}
      />;
  });

  const sortOrder = {
    'Brand Name': 1,
    'Equipment Name': 2,
    'Part Type': 3
  };

  const sortedFilters = props.filters.sort((a, b) => {
    return (sortOrder[a.field] || 4) - (sortOrder[b.field] || 4);
  });

  let filterDesc = sortedFilters.map(filter => {
    if (filter.value === 'Others') {
      return 'Uncategorized';
    }
    return filter.value;
  }).join(' ');

  console.log(filterDesc);
  let userSearchDesc = (props.keywords.length > 0 && props.keywords !== "*") ?
                          `<h5>You searched for: <strong><u>${props.keywords}</u></strong></h5>`
                          :
                          (filterDesc.length > 0 ? `<h2>${filterDesc} Parts</h2><hr/>`: `<h5>No results found for your query.</h5>`);
  if (props.keywords === "*") {
    if (filterDesc.length === 0) {
      userSearchDesc = "<h2>Showing All Parts</h2><hr/>"
    }
    else {
      userSearchDesc = `<h2>All ${filterDesc} Parts</h2><hr/>`
    }
  }
  let beginDocNumber = Math.min(props.skip + 1, props.count);
  let endDocNumber = Math.min(props.skip + props.top, props.count);

  return (
    <div>
      {/* <div><</div> */}
      <div>
      <p className="results-info" dangerouslySetInnerHTML={{__html: userSearchDesc}}/>
        <p className="results-info">Showing {beginDocNumber}-{endDocNumber} of {props.count.toLocaleString()} results</p>
        <div className="row row-cols-md-4 results">
          {results}
        </div>
      </div>
    </div>
  );
};
