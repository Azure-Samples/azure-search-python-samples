import React from 'react';
import Result from './Result/Result';

import "./Results.css";

function createUserSearchDescription(props, filterDesc) {
  const { keywords, resultFlag, modelBrandName, modelEquipmentType } = props;
    if (resultFlag === "exact_model") {
    return `<h2>${keywords.toUpperCase()} ${modelBrandName} ${modelEquipmentType} Parts</h2><hr/>`;
  }
  if (keywords.length > 0 && keywords !== "*") {
    if (resultFlag && resultFlag==="no result") {
      return `<h3>No results found for your query.</h3><hr/>`;
    }
    else {
      return `<h5>You searched for: <strong><u>${keywords.toLowerCase()}</u></strong></h5>`;
   }
    
  }
  if (keywords === "*") {
    return filterDesc.length === 0 ? 
      "<h2>Showing All Results</h2><hr/>" : 
      `<h2>All ${filterDesc} Parts</h2><hr/>`;
  }
  if (filterDesc.length > 0) {
    return `<h2>${filterDesc} Parts</h2><hr/>`;
  }

  return `<h3>No results found for your query.</h3><hr/>`;
}

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

  const sortedFilters = props.filters && props.filters.sort((a, b) => {
    return (sortOrder[a.field] || 4) - (sortOrder[b.field] || 4);
  });

  let filterDesc = sortedFilters && sortedFilters.map(filter => {
    if (filter.value === 'Others') {
      return 'Uncategorized';
    }
    return filter.value;
  }).join(' ');

  const userSearchDesc = createUserSearchDescription(props, filterDesc);

  let beginDocNumber = Math.min(props.skip + 1, props.count);
  let endDocNumber = Math.min(props.skip + props.top, props.count);

  return (
    <div>
      {/* <div><</div> */}
      <div>
      <div>
        <p className="results-info" dangerouslySetInnerHTML={{__html: userSearchDesc}}></p>
        {/* {props.keywords.length > 0 && props.keywords !== "*" && <span className="centered-symbol" id="clickableSymbol" onClick={() => { props.setQ("*"); }}>&#x2715;</span>} */}
      </div> 
        <p className="results-info">Showing {beginDocNumber}-{endDocNumber} of {props.count.toLocaleString()} results</p>
        <div className="row row-cols-md-4 results">
          {results}
        </div>
      </div>
    </div>
  );
};
